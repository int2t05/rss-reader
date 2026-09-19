"""配置加载:JSON 主配置 + YAML 源配置 + categories/<cat>/category.json,支持 ${VAR} 展开。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from src.models import CategoryConfig, RSSSourceConfig
from src.processing.categories import parse_category_config
from src.utils.env import expand_env

logger = logging.getLogger(__name__)


class Config:
    """运行时配置聚合:AI 设置、分类树、源列表、输出渠道。"""

    def __init__(
        self,
        ai: dict,
        categories: dict,
        category_configs: list[CategoryConfig],
        sources: list[RSSSourceConfig],
        outputs: dict,
        rsshub_base_url: str | None,
        data_dir: Path,
    ):
        self.ai = ai
        self.categories = categories  # raw dict from config.json
        self.category_configs = category_configs  # enabled only
        self.sources = sources  # enabled only
        self.outputs = outputs
        self.rsshub_base_url = rsshub_base_url
        self.data_dir = data_dir

    @property
    def enabled_category_names(self) -> list[str]:
        """启用分类名列表,供 Tier1/Tier2 路由使用。"""
        return [c.name for c in self.category_configs]


def _load_category_configs(categories_root: Path, raw_categories: dict) -> list[CategoryConfig]:
    """遍历 categories/<cat>/category.json,合并 raw 覆盖,过滤 enabled=False。

    委托 parse_category_config,与 CategoryRegistry 共享解析逻辑。
    """
    configs: list[CategoryConfig] = []
    for name, raw in raw_categories.items():
        cfg = parse_category_config(categories_root, name, raw)
        if cfg is not None:
            configs.append(cfg)
    return configs


def _load_feeds(feeds_root: Path) -> list[RSSSourceConfig]:
    """遍历 feeds/*.yml,合并为 RSSSourceConfig 列表,过滤 enabled=False,展开 ${VAR}。"""
    sources: list[RSSSourceConfig] = []
    if not feeds_root.exists():
        return sources
    for yml_file in sorted(feeds_root.glob("*.yml")):
        raw_list = yaml.safe_load(yml_file.read_text(encoding="utf-8")) or []
        if not isinstance(raw_list, list):
            continue
        for entry in raw_list:
            if not entry.get("enabled", True):
                continue
            try:
                sources.append(
                    RSSSourceConfig(
                        name=entry["name"],
                        url=expand_env(entry["url"]),
                        category=entry["category"],
                        enabled=True,
                        content_extractor=entry.get("content_extractor"),
                    )
                )
            except (KeyError, TypeError) as e:
                logger.warning("跳过缺字段的源条目(%s):%s", e, entry)
                continue
    return sources


def load_config(project_dir: Path | None = None, config_path: str | None = None) -> Config:
    """加载完整配置:data/config.json + categories/* + feeds/*。

    project_dir=None 时回退到当前工作目录。config_path 非空时覆盖默认 config.json 路径。
    """
    project_dir = Path.cwd() if project_dir is None else Path(project_dir)

    data_dir = project_dir / "data"
    config_file = Path(config_path) if config_path else data_dir / "config.json"
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    raw = json.loads(config_file.read_text(encoding="utf-8"))

    categories_root = project_dir / "categories"
    feeds_root = project_dir / "feeds"

    category_configs = _load_category_configs(categories_root, raw.get("categories", {}))
    sources = _load_feeds(feeds_root)

    return Config(
        ai=raw.get("ai", {}),
        categories=raw.get("categories", {}),
        category_configs=category_configs,
        sources=sources,
        outputs=raw.get("outputs", {}),
        rsshub_base_url=expand_env(raw.get("rsshub_base_url")) if raw.get("rsshub_base_url") else None,
        data_dir=data_dir,
    )
