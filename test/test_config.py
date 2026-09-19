"""配置加载测试:JSON + YAML + ${VAR} 环境变量展开。"""
import json
from pathlib import Path

import pytest

from src.config import load_config


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """构造最小可用的项目配置目录:data/config.json + categories/*.json + feeds/*.yml。"""
    (tmp_path / "data").mkdir()
    (tmp_path / "categories").mkdir()
    (tmp_path / "feeds").mkdir()

    (tmp_path / "data" / "config.json").write_text(
        json.dumps(
            {
                "ai": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "api_key_env": "OPENAI_API_KEY",
                    "analysis_concurrency": 5,
                },
                "rsshub_base_url": None,
                "categories": {
                    "ai-research": {
                        "enabled": True,
                        "display_name": "AI 研究",
                        "threshold": 7.0,
                        "digest_limit": 8,
                        "children": ["ai-vendor", "ai-researcher", "ai-papers"],
                    },
                    "finance": {
                        "enabled": False,
                        "display_name": "财经",
                        "threshold": 6.0,
                        "digest_limit": 3,
                        "children": [],
                    },
                },
                "outputs": {"github_pages": True, "webhook": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (tmp_path / "categories" / "ai-research").mkdir()
    (tmp_path / "categories" / "ai-research" / "category.json").write_text(
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

    (tmp_path / "feeds" / "ai-research.yml").write_text(
        "- name: Anthropic News\n"
        "  url: https://www.anthropic.com/news/rss.xml\n"
        "  category: ai-research/ai-vendor\n"
        "  enabled: true\n",
        encoding="utf-8",
    )

    return tmp_path


def test_load_config_reads_main_json(config_dir: Path):
    """load_config 读取 data/config.json,填充 ai/categories/outputs。"""
    cfg = load_config(config_dir)
    assert cfg.ai["provider"] == "openai"
    assert cfg.ai["model"] == "gpt-4o-mini"
    assert cfg.ai["analysis_concurrency"] == 5
    assert "ai-research" in cfg.categories
    assert cfg.outputs["github_pages"] is True


def test_load_config_reads_categories_dir(config_dir: Path):
    """load_config 遍历 categories/<cat>/category.json,构造 CategoryConfig 列表。"""
    cfg = load_config(config_dir)
    cats = {c.name: c for c in cfg.category_configs}
    assert "ai-research" in cats
    assert cats["ai-research"].threshold == 7.0
    assert cats["ai-research"].children == ["ai-vendor", "ai-researcher", "ai-papers"]


def test_load_config_filters_disabled_categories(config_dir: Path):
    """enabled=False 的分类(如 finance)不进 category_configs,但保留在 raw categories dict。"""
    cfg = load_config(config_dir)
    cat_names = [c.name for c in cfg.category_configs]
    assert "ai-research" in cat_names
    assert "finance" not in cat_names  # 被过滤
    assert "finance" in cfg.categories  # 但 raw 保留


def test_load_config_reads_feeds_yml(config_dir: Path):
    """load_config 遍历 feeds/*.yml,合并为 RSSSourceConfig 列表。"""
    cfg = load_config(config_dir)
    assert len(cfg.sources) == 1
    src = cfg.sources[0]
    assert src.name == "Anthropic News"
    assert src.url == "https://www.anthropic.com/news/rss.xml"
    assert src.category == "ai-research/ai-vendor"
    assert src.enabled is True


def test_load_config_expands_env_var_in_url(config_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """feeds/*.yml 中 url 含 ${VAR} 时展开为环境变量值。"""
    monkeypatch.setenv("LWN_TOKEN", "secret-token-123")
    (config_dir / "feeds" / "systems.yml").write_text(
        "- name: LWN.net\n"
        "  url: https://lwn.net/headlines/rss/${LWN_TOKEN}\n"
        "  category: systems/eng-blog\n",
        encoding="utf-8",
    )
    cfg = load_config(config_dir)
    lwn = next(s for s in cfg.sources if s.name == "LWN.net")
    assert lwn.url == "https://lwn.net/headlines/rss/secret-token-123"


def test_load_config_filters_disabled_sources(config_dir: Path):
    """feeds/*.yml 中 enabled: false 的源被过滤。"""
    (config_dir / "feeds" / "systems.yml").write_text(
        "- name: Dead Feed\n"
        "  url: https://example.com/feed.xml\n"
        "  category: systems/eng-blog\n"
        "  enabled: false\n",
        encoding="utf-8",
    )
    cfg = load_config(config_dir)
    assert all(s.name != "Dead Feed" for s in cfg.sources)


def test_load_config_missing_dir_raises(tmp_path: Path):
    """data/config.json 不存在时报清晰错误。"""
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path)


def test_load_config_rsshub_base_url_none(config_dir: Path):
    """rsshub_base_url 为 None 时,配置正常加载。"""
    cfg = load_config(config_dir)
    assert cfg.rsshub_base_url is None


def test_config_default_data_dir_when_none(monkeypatch: pytest.MonkeyPatch, config_dir: Path):
    """data_dir=None 时回退到项目根 data/。"""
    monkeypatch.chdir(config_dir)
    cfg = load_config(None)
    assert cfg.ai["provider"] == "openai"
