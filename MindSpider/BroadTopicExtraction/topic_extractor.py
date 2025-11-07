#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BroadTopicExtraction模块 - 话题提取器
基于DeepSeek直接提取关键词和生成新闻总结
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from openai import OpenAI
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 添加项目根目录的父目录到路径（用于访问utils）
project_root_parent = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root_parent))

try:
    import config
    from config import settings
except ImportError:
    raise ImportError("无法导入settings.py配置文件")

try:
    from utils.scenario_loader import get_scenario_loader, ScenarioConfig
except ImportError as e:
    logger.warning(f"无法导入场景加载器: {e}，将使用默认提示词")
    get_scenario_loader = None
    ScenarioConfig = None

class TopicExtractor:
    """话题提取器"""

    def __init__(self, scenario_id: str = "default"):
        """
        初始化话题提取器
        
        Args:
            scenario_id: 场景配置ID（如"default"、"ai_tech"、"prompt_engineering"等）
        """
        self.client = OpenAI(
            api_key=settings.MINDSPIDER_API_KEY,
            base_url=settings.MINDSPIDER_BASE_URL
        )
        self.model = settings.MINDSPIDER_MODEL_NAME
        
        # 加载场景配置
        self.scenario: Optional[ScenarioConfig] = None
        if get_scenario_loader is not None:
            try:
                loader = get_scenario_loader()
                self.scenario = loader.get_scenario(scenario_id)
                if not self.scenario:
                    logger.warning(f"场景 {scenario_id} 不存在，使用默认场景")
                    self.scenario = loader.get_default_scenario()
                logger.info(f"使用场景配置: {self.scenario.name}")
            except Exception as e:
                logger.error(f"加载场景配置失败: {e}，将使用默认提示词")
                self.scenario = None
        else:
            logger.warning("场景加载器不可用，将使用默认提示词")
    
    def extract_keywords_and_summary(self, news_list: List[Dict], max_keywords: int = 100) -> Tuple[List[str], str]:
        """
        从新闻列表中提取关键词和生成总结
        
        Args:
            news_list: 新闻列表
            max_keywords: 最大关键词数量
            
        Returns:
            (关键词列表, 新闻分析总结)
        """
        if not news_list:
            return [], "今日暂无热点新闻"
        
        # 构建新闻摘要文本
        news_text = self._build_news_summary(news_list)
        
        # 构建提示词
        prompt = self._build_analysis_prompt(news_text, max_keywords)
        
        # 获取system prompt
        system_prompt = "你是一个专业的新闻分析师，擅长从热点新闻中提取关键词和撰写分析总结。"
        if self.scenario and 'topic_extraction' in self.scenario.crawler:
            system_prompt = self.scenario.crawler['topic_extraction'].get('system_prompt', system_prompt)
        
        try:
            # 调用API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            # 解析返回结果
            result_text = response.choices[0].message.content
            keywords, summary = self._parse_analysis_result(result_text)
            
            # 应用关键词过滤规则
            keywords = self._apply_keyword_filters(keywords)
            
            print(f"成功提取 {len(keywords)} 个关键词并生成新闻总结")
            return keywords[:max_keywords], summary
            
        except Exception as e:
            print(f"话题提取失败: {e}")
            # 返回简单的fallback结果
            fallback_keywords = self._extract_simple_keywords(news_list)
            fallback_summary = f"今日共收集到 {len(news_list)} 条热点新闻，涵盖多个平台的热门话题。"
            return fallback_keywords[:max_keywords], fallback_summary
    
    def _build_news_summary(self, news_list: List[Dict]) -> str:
        """构建新闻摘要文本"""
        news_items = []
        
        for i, news in enumerate(news_list, 1):
            title = news.get('title', '无标题')
            source = news.get('source_platform', news.get('source', '未知'))
            
            # 清理标题中的特殊字符
            title = re.sub(r'[#@]', '', title).strip()
            
            news_items.append(f"{i}. 【{source}】{title}")
        
        return "\n".join(news_items)
    
    def _build_analysis_prompt(self, news_text: str, max_keywords: int) -> str:
        """构建分析提示词（从场景配置加载）"""
        news_count = len(news_text.split('\n'))
        
        # 如果有场景配置，使用场景的提示词模板
        if self.scenario and 'topic_extraction' in self.scenario.crawler:
            template = self.scenario.crawler['topic_extraction'].get('user_prompt_template', '')
            if template:
                # 填充变量
                try:
                    prompt = template.format(
                        news_count=news_count,
                        news_text=news_text,
                        max_keywords=max_keywords
                    )
                    return prompt
                except Exception as e:
                    logger.error(f"格式化场景提示词失败: {e}，使用默认提示词")
        
        # 默认提示词（fallback）
        prompt = f"""
请分析以下{news_count}条今日热点新闻，完成两个任务：

新闻列表：
{news_text}

任务1：提取关键词（最多{max_keywords}个）
- 提取能代表今日热点话题的关键词
- 关键词应该适合用于社交媒体平台搜索
- 优先选择热度高、讨论量大的话题
- 避免过于宽泛或过于具体的词汇

任务2：撰写新闻分析总结（150-300字）
- 简要概括今日热点新闻的主要内容
- 指出当前社会关注的重点话题方向
- 分析这些热点反映的社会现象或趋势
- 语言简洁明了，客观中性

请严格按照以下JSON格式输出：
```json
{{
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "summary": "今日新闻分析总结内容..."
}}
```

请直接输出JSON格式的结果，不要包含其他文字说明。
"""
        return prompt
    
    def _parse_analysis_result(self, result_text: str) -> Tuple[List[str], str]:
        """解析分析结果"""
        try:
            # 尝试提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # 如果没有代码块，尝试直接解析
                json_text = result_text.strip()
            
            # 解析JSON
            data = json.loads(json_text)
            
            keywords = data.get('keywords', [])
            summary = data.get('summary', '')
            
            # 验证和清理关键词
            clean_keywords = []
            for keyword in keywords:
                keyword = str(keyword).strip()
                if keyword and len(keyword) > 1 and keyword not in clean_keywords:
                    clean_keywords.append(keyword)
            
            # 验证总结
            if not summary or len(summary.strip()) < 10:
                summary = "今日热点新闻涵盖多个领域，反映了当前社会的多元化关注点。"
            
            return clean_keywords, summary.strip()
            
        except json.JSONDecodeError as e:
            print(f"解析JSON失败: {e}")
            print(f"原始返回: {result_text}")
            
            # 尝试手动解析
            return self._manual_parse_result(result_text)
        
        except Exception as e:
            print(f"处理分析结果失败: {e}")
            return [], "分析结果处理失败，请稍后重试。"
    
    def _manual_parse_result(self, text: str) -> Tuple[List[str], str]:
        """手动解析结果（当JSON解析失败时的后备方案）"""
        print("尝试手动解析结果...")
        
        keywords = []
        summary = ""
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 寻找关键词
            if '关键词' in line or 'keywords' in line.lower():
                # 提取关键词
                keyword_match = re.findall(r'[""](.*?)["""]', line)
                if keyword_match:
                    keywords.extend(keyword_match)
                else:
                    # 尝试其他分隔符
                    parts = re.split(r'[,，、]', line)
                    for part in parts:
                        clean_part = re.sub(r'[关键词：:keywords\[\]"]', '', part).strip()
                        if clean_part and len(clean_part) > 1:
                            keywords.append(clean_part)
            
            # 寻找总结
            elif '总结' in line or '分析' in line or 'summary' in line.lower():
                if '：' in line or ':' in line:
                    summary = line.split('：')[-1].split(':')[-1].strip()
            
            # 如果这一行看起来像总结内容
            elif len(line) > 50 and ('今日' in line or '热点' in line or '新闻' in line):
                if not summary:
                    summary = line
        
        # 清理关键词
        clean_keywords = []
        for keyword in keywords:
            keyword = keyword.strip()
            if keyword and len(keyword) > 1 and keyword not in clean_keywords:
                clean_keywords.append(keyword)
        
        # 如果没有找到总结，生成一个简单的
        if not summary:
            summary = "今日热点新闻内容丰富，涵盖了社会各个层面的关注点。"
        
        return clean_keywords[:max_keywords], summary
    
    def _apply_keyword_filters(self, keywords: List[str]) -> List[str]:
        """应用关键词过滤规则"""
        # 如果没有场景配置或没有过滤规则，直接返回
        if not self.scenario or 'topic_extraction' not in self.scenario.crawler:
            return keywords
        
        filters = self.scenario.crawler['topic_extraction'].get('keyword_filters', {})
        if not filters:
            return keywords
        
        filtered = []
        
        include_patterns = filters.get('include_patterns', [])
        exclude_patterns = filters.get('exclude_patterns', [])
        min_length = filters.get('min_length', 2)
        max_length = filters.get('max_length', 50)
        
        for kw in keywords:
            # 长度检查
            if len(kw) < min_length or len(kw) > max_length:
                continue
            
            # 排除模式检查
            if exclude_patterns:
                if any(re.search(pattern, kw) for pattern in exclude_patterns):
                    continue
            
            # 包含模式检查（如果指定了，必须匹配至少一个）
            if include_patterns:
                if not any(re.search(pattern, kw) for pattern in include_patterns):
                    continue
            
            filtered.append(kw)
        
        logger.info(f"关键词过滤: {len(keywords)} -> {len(filtered)}")
        return filtered
    
    def _extract_simple_keywords(self, news_list: List[Dict]) -> List[str]:
        """简单关键词提取（fallback方案）"""
        keywords = []
        
        for news in news_list:
            title = news.get('title', '')
            
            # 简单的关键词提取
            # 移除常见的无意义词汇
            title_clean = re.sub(r'[#@【】\[\]()（）]', ' ', title)
            words = title_clean.split()
            
            for word in words:
                word = word.strip()
                if (len(word) > 1 and 
                    word not in ['的', '了', '在', '和', '与', '或', '但', '是', '有', '被', '将', '已', '正在'] and
                    word not in keywords):
                    keywords.append(word)
        
        return keywords[:10]
    
    def get_search_keywords(self, keywords: List[str], limit: int = 10) -> List[str]:
        """
        获取用于搜索的关键词
        
        Args:
            keywords: 关键词列表
            limit: 限制数量
            
        Returns:
            适合搜索的关键词列表
        """
        # 过滤和优化关键词
        search_keywords = []
        
        for keyword in keywords:
            keyword = str(keyword).strip()
            
            # 过滤条件
            if (len(keyword) > 1 and 
                len(keyword) < 20 and  # 不能太长
                keyword not in search_keywords and
                not keyword.isdigit() and  # 不是纯数字
                not re.match(r'^[a-zA-Z]+$', keyword)):  # 不是纯英文（除非是专有名词）
                
                search_keywords.append(keyword)
        
        return search_keywords[:limit]

if __name__ == "__main__":
    # 测试话题提取器
    import sys
    
    # 从命令行获取场景ID（可选）
    scenario_id = sys.argv[1] if len(sys.argv) > 1 else "default"
    print(f"使用场景: {scenario_id}")
    
    extractor = TopicExtractor(scenario_id=scenario_id)
    
    # 模拟新闻数据
    test_news = [
        {"title": "AI技术发展迅速", "source_platform": "科技新闻"},
        {"title": "股市行情分析", "source_platform": "财经新闻"},
        {"title": "明星最新动态", "source_platform": "娱乐新闻"}
    ]
    
    keywords, summary = extractor.extract_keywords_and_summary(test_news)
    
    print(f"提取的关键词: {keywords}")
    print(f"新闻总结: {summary}")
    
    search_keywords = extractor.get_search_keywords(keywords)
    print(f"搜索关键词: {search_keywords}")
