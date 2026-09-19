"""CategoryRegistry 测试:加载分类配置 + prompt 文件,按路径/前缀查询。

真实文件 I/O,无 mock。使用 tmp_path 构造最小 categories/ 目录。
"""
import json
from pathlib import Path

import pytest

from src.processing.categories import CategoryRegistry


@pytest.fixture
def categories_root(tmp_path: Path) -> Path:
    """构造 categories/ 目录:两个分类,各含 category.json + analysis.md + agent_system.md。"""
    root = tmp_path / "categories"

    ai_dir = root / "ai-research"
    ai_dir.mkdir(parents=True)
    (ai_dir / "category.json").write_text(
        json.dumps(
            {
                "enabled": True,
                "display_name": "AI 研究",
                "threshold": 7.0,
                "digest_limit": 8,
                "children": ["ai-vendor", "ai-researcher", "ai-papers"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (ai_dir / "analysis.md").write_text("# AI 研究打分标准\n9-10 分:重大突破", encoding="utf-8")
    (ai_dir / "agent_system.md").write_text("# AI 研究分析员\n你是 AI 领域分析员", encoding="utf-8")

    sys_dir = root / "systems"
    sys_dir.mkdir(parents=True)
    (sys_dir / "category.json").write_text(
        json.dumps(
            {
                "enabled": True,
                "display_name": "系统工程",
                "threshold": 5.0,
                "digest_limit": 5,
                "children": ["eng-blog", "framework", "cn-tech"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (sys_dir / "analysis.md").write_text("# 系统工程打分标准", encoding="utf-8")
    (sys_dir / "agent_system.md").write_text("# 系统工程师\n你是系统工程分析员", encoding="utf-8")

    # 预留但 disabled
    fin_dir = root / "finance"
    fin_dir.mkdir(parents=True)
    (fin_dir / "category.json").write_text(
        json.dumps({"enabled": False, "display_name": "财经", "threshold": 6.0, "digest_limit": 3, "children": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    return root


def test_registry_loads_enabled_categories(categories_root: Path):
    """CategoryRegistry 加载 enabled 分类,过滤 disabled。"""
    reg = CategoryRegistry(categories_root)
    reg.load_from_raw({"ai-research": {"enabled": True}, "systems": {"enabled": True}, "finance": {"enabled": False}})
    names = [c.name for c in reg.all()]
    assert "ai-research" in names
    assert "systems" in names
    assert "finance" not in names


def test_registry_get_by_name(categories_root: Path):
    """按分类名获取 CategoryConfig。"""
    reg = CategoryRegistry(categories_root)
    reg.load_from_raw({"ai-research": {"enabled": True}, "systems": {"enabled": True}})
    cat = reg.get("ai-research")
    assert cat is not None
    assert cat.threshold == 7.0
    assert cat.digest_limit == 8


def test_registry_get_unknown_returns_none(categories_root: Path):
    """未知分类返回 None。"""
    reg = CategoryRegistry(categories_root)
    reg.load_from_raw({"ai-research": {"enabled": True}})
    assert reg.get("nonexistent") is None


def test_registry_get_by_path_finds_parent(categories_root: Path):
    """按路径(如 ai-research/ai-vendor)查询时,匹配父分类 ai-research。"""
    reg = CategoryRegistry(categories_root)
    reg.load_from_raw({"ai-research": {"enabled": True}, "systems": {"enabled": True}})
    cat = reg.get_by_path("ai-research/ai-vendor")
    assert cat is not None
    assert cat.name == "ai-research"


def test_registry_get_by_path_exact_match(categories_root: Path):
    """路径恰好等于分类名时直接匹配。"""
    reg = CategoryRegistry(categories_root)
    reg.load_from_raw({"ai-research": {"enabled": True}})
    cat = reg.get_by_path("ai-research")
    assert cat is not None
    assert cat.name == "ai-research"


def test_registry_get_by_path_no_match(categories_root: Path):
    """无匹配前缀时返回 None。"""
    reg = CategoryRegistry(categories_root)
    reg.load_from_raw({"ai-research": {"enabled": True}})
    assert reg.get_by_path("unknown/sub") is None


def test_registry_category_tree_json(categories_root: Path):
    """category_tree_json 返回分类树 JSON 字符串,供 prompt 注入。"""
    reg = CategoryRegistry(categories_root)
    reg.load_from_raw({"ai-research": {"enabled": True}, "systems": {"enabled": True}})
    tree = reg.category_tree_json()
    assert "ai-research" in tree
    assert "systems" in tree
    assert "ai-vendor" in tree  # children


def test_registry_empty_root(tmp_path: Path):
    """空 categories/ 目录 + 空 raw 时,registry 为空。"""
    reg = CategoryRegistry(tmp_path / "empty")
    reg.load_from_raw({})
    assert reg.all() == []
    assert reg.get("anything") is None
