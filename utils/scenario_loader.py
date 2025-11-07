"""
场景配置加载器
负责加载和管理不同分析场景的配置
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class ScenarioMetadata:
    """场景元数据"""
    name: str
    description: str
    version: str
    author: str = "BettaFish Team"


@dataclass
class ScenarioConfig:
    """场景配置"""
    metadata: ScenarioMetadata
    crawler: Dict[str, Any]
    query_engine: Dict[str, Any]
    media_engine: Dict[str, Any]
    insight_engine: Dict[str, Any]
    report_engine: Dict[str, Any]
    
    @property
    def name(self) -> str:
        return self.metadata.name
    
    @property
    def description(self) -> str:
        return self.metadata.description


class ScenarioLoader:
    """场景配置加载器"""
    
    def __init__(self, scenarios_dir: str = "scenarios"):
        self.scenarios_dir = Path(scenarios_dir)
        self._scenarios_cache: Dict[str, ScenarioConfig] = {}
        self._load_all_scenarios()
    
    def _load_all_scenarios(self):
        """加载所有场景配置"""
        if not self.scenarios_dir.exists():
            logger.warning(f"场景配置目录不存在: {self.scenarios_dir}")
            self.scenarios_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for yaml_file in self.scenarios_dir.glob("*.yaml"):
            try:
                scenario = self._load_scenario_file(yaml_file)
                scenario_id = yaml_file.stem
                self._scenarios_cache[scenario_id] = scenario
                logger.info(f"成功加载场景配置: {scenario_id} - {scenario.name}")
            except Exception as e:
                logger.error(f"加载场景配置失败 {yaml_file}: {e}")
    
    def _load_scenario_file(self, yaml_file: Path) -> ScenarioConfig:
        """加载单个场景配置文件"""
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 验证必需字段
        if 'metadata' not in data:
            raise ValueError(f"配置文件缺少metadata字段: {yaml_file}")
        
        metadata = ScenarioMetadata(
            name=data['metadata']['name'],
            description=data['metadata']['description'],
            version=data['metadata']['version'],
            author=data['metadata'].get('author', 'BettaFish Team')
        )
        
        return ScenarioConfig(
            metadata=metadata,
            crawler=data.get('crawler', {}),
            query_engine=data.get('query_engine', {}),
            media_engine=data.get('media_engine', {}),
            insight_engine=data.get('insight_engine', {}),
            report_engine=data.get('report_engine', {})
        )
    
    def get_scenario(self, scenario_id: str) -> Optional[ScenarioConfig]:
        """获取指定场景配置"""
        return self._scenarios_cache.get(scenario_id)
    
    def list_scenarios(self) -> List[Dict[str, str]]:
        """列出所有可用场景"""
        return [
            {
                "id": scenario_id,
                "name": scenario.name,
                "description": scenario.description,
                "version": scenario.metadata.version
            }
            for scenario_id, scenario in self._scenarios_cache.items()
        ]
    
    def get_default_scenario(self) -> ScenarioConfig:
        """获取默认场景"""
        default = self.get_scenario("default")
        if default:
            return default
        
        # 如果没有default，返回第一个可用的
        if self._scenarios_cache:
            first_scenario = list(self._scenarios_cache.values())[0]
            logger.warning(f"未找到default场景，使用 {first_scenario.name}")
            return first_scenario
        
        raise ValueError("没有可用的场景配置")


# 全局实例
_scenario_loader: Optional[ScenarioLoader] = None


def get_scenario_loader() -> ScenarioLoader:
    """获取场景加载器单例"""
    global _scenario_loader
    if _scenario_loader is None:
        _scenario_loader = ScenarioLoader()
    return _scenario_loader

