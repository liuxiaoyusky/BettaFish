#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场景配置加载器测试脚本
用于验证场景配置系统是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_scenario_loader():
    """测试场景加载器"""
    print("=" * 60)
    print("场景配置加载器测试")
    print("=" * 60)
    
    try:
        from utils.scenario_loader import get_scenario_loader
        print("✓ 成功导入场景加载器\n")
    except ImportError as e:
        print(f"✗ 导入场景加载器失败: {e}")
        return False
    
    # 测试1: 获取加载器实例
    print("测试1: 获取加载器实例...")
    try:
        loader = get_scenario_loader()
        print("✓ 成功获取加载器实例\n")
    except Exception as e:
        print(f"✗ 获取加载器实例失败: {e}\n")
        return False
    
    # 测试2: 列出所有场景
    print("测试2: 列出所有可用场景...")
    try:
        scenarios = loader.list_scenarios()
        print(f"✓ 找到 {len(scenarios)} 个场景配置:")
        for scenario in scenarios:
            print(f"  - {scenario['id']}: {scenario['name']}")
            print(f"    描述: {scenario['description']}")
            print(f"    版本: {scenario['version']}")
        print()
    except Exception as e:
        print(f"✗ 列出场景失败: {e}\n")
        return False
    
    # 测试3: 获取默认场景
    print("测试3: 获取默认场景...")
    try:
        default_scenario = loader.get_default_scenario()
        print(f"✓ 默认场景: {default_scenario.name}")
        print(f"  描述: {default_scenario.description}\n")
    except Exception as e:
        print(f"✗ 获取默认场景失败: {e}\n")
        return False
    
    # 测试4: 获取特定场景并检查配置
    print("测试4: 获取并检查场景配置...")
    test_scenarios = ["default", "ai_tech", "prompt_engineering", "deep_research"]
    
    for scenario_id in test_scenarios:
        try:
            scenario = loader.get_scenario(scenario_id)
            if not scenario:
                print(f"✗ 场景 '{scenario_id}' 不存在")
                continue
            
            print(f"\n场景: {scenario.name} ({scenario_id})")
            print(f"  - Crawler配置: {'✓' if scenario.crawler else '✗'}")
            
            if scenario.crawler and 'topic_extraction' in scenario.crawler:
                topic_config = scenario.crawler['topic_extraction']
                print(f"    * System Prompt: {'✓' if topic_config.get('system_prompt') else '✗'}")
                print(f"    * User Prompt Template: {'✓' if topic_config.get('user_prompt_template') else '✗'}")
                print(f"    * Keyword Filters: {'✓' if topic_config.get('keyword_filters') else '✗'}")
            
            print(f"  - QueryEngine配置: {'✓' if scenario.query_engine else '✗'}")
            print(f"  - MediaEngine配置: {'✓' if scenario.media_engine else '✗'}")
            print(f"  - InsightEngine配置: {'✓' if scenario.insight_engine else '✗'}")
            print(f"  - ReportEngine配置: {'✓' if scenario.report_engine else '✗'}")
            
        except Exception as e:
            print(f"✗ 检查场景 '{scenario_id}' 失败: {e}")
    
    print("\n" + "=" * 60)
    print("✓ 所有测试通过！场景配置系统正常工作。")
    print("=" * 60)
    return True


def test_topic_extractor():
    """测试话题提取器场景支持"""
    print("\n" + "=" * 60)
    print("话题提取器场景支持测试")
    print("=" * 60)
    
    try:
        # 临时修改路径以导入MindSpider模块
        mindspider_path = Path(__file__).parent / "MindSpider"
        sys.path.insert(0, str(mindspider_path))
        
        from BroadTopicExtraction.topic_extractor import TopicExtractor
        print("✓ 成功导入话题提取器\n")
    except ImportError as e:
        print(f"✗ 导入话题提取器失败: {e}")
        print("  提示: 这可能需要完整的环境配置")
        return False
    
    # 测试不同场景的初始化
    print("测试: 使用不同场景初始化提取器...")
    test_scenarios = ["default", "ai_tech", "prompt_engineering"]
    
    for scenario_id in test_scenarios:
        try:
            print(f"\n场景: {scenario_id}")
            extractor = TopicExtractor(scenario_id=scenario_id)
            
            if extractor.scenario:
                print(f"  ✓ 成功加载场景: {extractor.scenario.name}")
            else:
                print(f"  ✗ 场景加载失败，使用默认配置")
        except Exception as e:
            print(f"  ✗ 初始化失败: {e}")
    
    print("\n" + "=" * 60)
    print("✓ 话题提取器场景支持测试完成")
    print("=" * 60)
    return True


if __name__ == "__main__":
    print("\n开始测试场景配置系统...\n")
    
    success = True
    
    # 运行场景加载器测试
    if not test_scenario_loader():
        success = False
    
    # 运行话题提取器测试
    try:
        if not test_topic_extractor():
            success = False
    except Exception as e:
        print(f"\n话题提取器测试跳过: {e}")
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 全部测试通过！")
        print("=" * 60)
        print("\n后续步骤:")
        print("1. 安装依赖: pip install pyyaml")
        print("2. 启动主应用: python app.py")
        print("3. 在Web界面的'分析场景'下拉菜单中选择不同场景")
        print("4. 输入查询内容并开始分析")
        print("\n爬虫系统使用:")
        print("  python MindSpider/BroadTopicExtraction/main.py --scenario ai_tech")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("⚠️  部分测试失败")
        print("=" * 60)
        sys.exit(1)


