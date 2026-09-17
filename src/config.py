"""配置加载:JSON 主配置 + YAML 源配置 + categories/<cat>/category.json,支持 ${VAR} 展开。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

from src.models import CategoryConfig, RSSSourceConfig

_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def _expand_env(value: str) -> str:
    """将 ${VAR_NAME} 替换为 os.environ['VAR_NAME'],未定义时保留原样。

    示例:"https://lwn.net/${LWN_TOKEN}" → "https://lwn.net/secret-123"
    """
    # TODO: 与 sources/rss.py 中的 _expand_env 重复,应提取到 utils/env.py 共享
    return _ENV_VAR_PATTERN.sub(
        lambda m: os.environ.get(m.group(1), m.group(0)).strip(),
        value,
    )


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

    优先使用 categories/<cat>/category.json(独立文件),回退到 data/config.json 中
    categories 段的 raw 值,使配置可以只写一处。
    """
    configs: list[CategoryConfig] = []
    for name, raw in raw_categories.items():
        if not raw.get("enabled", False):
            continue
        # 独立 category.json 覆盖 raw(若存在)
        cat_file = categories_root / name / "category.json"
        merged = dict(raw)
        if cat_file.exists():
            merged.update(json.loads(cat_file.read_text(encoding="utf-8")))
        configs.append(
            CategoryConfig(
                name=name,
                enabled=merged.get("enabled", False),
                display_name=merged.get("display_name", {"en": name, "zh": name}),
                threshold=merged.get("threshold", 5.0),
                digest_limit=merged.get("digest_limit", 5),
                children=merged.get("children", []),
            )
        )
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
            # TODO: entry["name"]/entry["url"]/entry["category"] 缺字段时抛 KeyError 中断全部加载,应 try/except
            sources.append(
                RSSSourceConfig(
                    name=entry["name"],
                    url=_expand_env(entry["url"]),
                    category=entry["category"],
                    enabled=True,
                    content_extractor=entry.get("content_extractor"),
                )
            )
    return sources


def load_config(project_dir: Path | None) -> Config:
    """加载完整配置:data/config.json + categories/* + feeds/*。

    project_dir=None 时回退到当前工作目录。
    """
    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir)

    data_dir = project_dir / "data"
    config_file = data_dir / "config.json"
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
        # TODO: rsshub_base_url 未做 ${VAR} 展开,依赖 rss.py 二次 _expand_env,隐式依赖
        rsshub_base_url=raw.get("rsshub_base_url"),
        data_dir=data_dir,
    )
