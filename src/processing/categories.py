"""CategoryRegistry:加载分类配置,按路径/前缀查询。

分类树配置在 data/config.json 的 categories 段 + categories/<cat>/category.json。
Tier1/Tier2 的 prompt 在 src/ai/prompting/ 下(Python 生成,非 .md 文件)。
"""

from __future__ import annotations

import json
from pathlib import Path

from src.models import CategoryConfig


def parse_category_config(categories_root: Path, name: str, raw: dict) -> CategoryConfig | None:
    """解析单个分类:合并 categories/<name>/category.json 覆盖 raw,enabled=False 返回 None。

    config.py 与 CategoryRegistry 共享此逻辑,避免同一份配置解析两次。
    """
    if not raw.get("enabled", False):
        return None
    cat_file = categories_root / name / "category.json"
    merged = dict(raw)
    if cat_file.exists():
        merged.update(json.loads(cat_file.read_text(encoding="utf-8")))
    return CategoryConfig(
        name=name,
        enabled=merged.get("enabled", False),
        display_name=merged.get("display_name", name),
        threshold=merged.get("threshold", 5.0),
        digest_limit=merged.get("digest_limit", 5),
        children=merged.get("children", []),
    )


class CategoryRegistry:
    """分类树注册表:加载 enabled 分类,按名/路径查询。"""

    def __init__(self, categories_root: Path):
        """指定 categories/ 根目录,用于读取 category.json 覆盖配置。"""
        self._root = Path(categories_root)
        self._categories: dict[str, CategoryConfig] = {}

    def load_from_raw(self, raw_categories: dict) -> None:
        """从 config.json 的 categories 段加载,过滤 enabled=False。"""
        self._categories.clear()
        for name, raw in raw_categories.items():
            cfg = parse_category_config(self._root, name, raw)
            if cfg is not None:
                self._categories[name] = cfg

    def all(self) -> list[CategoryConfig]:
        """返回所有已加载(enabled)分类。"""
        return list(self._categories.values())

    def get(self, name: str) -> CategoryConfig | None:
        """按分类名精确查询。"""
        return self._categories.get(name)

    def get_by_path(self, category_path: str) -> CategoryConfig | None:
        """按分类路径查询:精确匹配或前缀匹配(路径首段为分类名)。

        示例:"ai-research/ai-vendor" → 匹配 "ai-research"
        """
        if not category_path:
            return None
        if category_path in self._categories:
            return self._categories[category_path]
        prefix = category_path.split("/", 1)[0]
        return self._categories.get(prefix)

    def category_tree_json(self) -> str:
        """生成分类树 JSON 字符串,供 Tier1 prompt 注入。"""
        tree = {
            name: {
                "display_name": cat.display_name,
                "threshold": cat.threshold,
                "children": cat.children,
            }
            for name, cat in self._categories.items()
        }
        return json.dumps(tree, ensure_ascii=False, indent=2)

