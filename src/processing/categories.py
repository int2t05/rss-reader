"""CategoryRegistry:加载分类配置 + prompt 文件,按路径/前缀查询,替代 Horizon 的 ProfileRegistry。

分类树配置在 data/config.json 的 categories 段,prompt 在 categories/<cat>/analysis.md
与 agent_system.md。Registry 合并两处,按分类名/路径前缀查询。

TODO: categories/<cat>/ 目录下缺 analysis.md 与 agent_system.md(仅测试 fixture 创建),
生产环境 get_analysis_prompt/get_agent_prompt 对所有分类返回 None,AI 分析质量下降。
TODO: load_from_raw 与 config.py _load_category_configs 逻辑重复,同一份配置解析两次。
"""

from __future__ import annotations

import json
from pathlib import Path

from src.models import CategoryConfig


class CategoryRegistry:
    """分类树注册表:加载 enabled 分类 + 关联 prompt 文件,按名/路径查询。"""

    def __init__(self, categories_root: Path):
        """指定 categories/ 根目录,用于读取 prompt 文件。"""
        self._root = Path(categories_root)
        self._categories: dict[str, CategoryConfig] = {}

    def load_from_raw(self, raw_categories: dict) -> None:
        """从 config.json 的 categories 段加载,过滤 enabled=False。"""
        self._categories.clear()
        for name, raw in raw_categories.items():
            if not raw.get("enabled", False):
                continue
            # categories/<name>/category.json 覆盖 raw(若存在)
            cat_file = self._root / name / "category.json"
            merged = dict(raw)
            if cat_file.exists():
                merged.update(json.loads(cat_file.read_text(encoding="utf-8")))
            self._categories[name] = CategoryConfig(
                name=name,
                enabled=merged.get("enabled", False),
                display_name=merged.get("display_name", {"en": name, "zh": name}),
                threshold=merged.get("threshold", 5.0),
                digest_limit=merged.get("digest_limit", 5),
                children=merged.get("children", []),
            )

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

    def get_analysis_prompt(self, name: str) -> str | None:
        """读取 categories/<name>/analysis.md 内容,无文件返回 None。"""
        if name not in self._categories:
            return None
        path = self._root / name / "analysis.md"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def get_agent_prompt(self, name: str) -> str | None:
        """读取 categories/<name>/agent_system.md 内容,无文件返回 None。"""
        if name not in self._categories:
            return None
        path = self._root / name / "agent_system.md"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

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
