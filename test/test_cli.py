"""CLI 入口测试:--check-config / --fetch-only / 参数解析。

非 mock:真实加载 tmp_path 下的配置目录,真实抓取 HN 验证 --fetch-only。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.main import build_parser, run_check_config, run_fetch_only


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """最小项目目录:data/config.json + categories/ + feeds/。"""
    (tmp_path / "data").mkdir()
    (tmp_path / "categories").mkdir()
    (tmp_path / "feeds").mkdir()
    (tmp_path / "data" / "config.json").write_text(
        json.dumps(
            {
                "ai": {"provider": "openai", "model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY"},
                "rsshub_base_url": None,
                "categories": {
                    "ai-research": {
                        "enabled": True,
                        "display_name": {"en": "AI Research", "zh": "AI 研究"},
                        "threshold": 7.0,
                        "digest_limit": 8,
                        "children": ["ai-vendor", "ai-researcher", "ai-papers"],
                    }
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
                "display_name": {"en": "AI Research", "zh": "AI 研究"},
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
        "  category: ai-research/ai-vendor\n",
        encoding="utf-8",
    )
    return tmp_path


def test_build_parser_defaults():
    """argparse 默认:--hours 24,--log-level WARNING。"""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.hours == 24
    assert args.log_level == "WARNING"
    assert args.check_config is False
    assert args.fetch_only is False
    assert args.data_dir is None
    assert args.config is None


def test_build_parser_custom_args():
    """argparse 解析自定义参数:--hours 48 --log-level DEBUG --fetch-only。"""
    parser = build_parser()
    args = parser.parse_args(["--hours", "48", "--log-level", "DEBUG", "--fetch-only", "--data-dir", "/tmp/data"])
    assert args.hours == 48
    assert args.log_level == "DEBUG"
    assert args.fetch_only is True
    assert args.data_dir == "/tmp/data"


def test_build_parser_classify_only():
    """--classify-only 标志可解析。"""
    parser = build_parser()
    args = parser.parse_args(["--classify-only", "--limit", "10"])
    assert args.classify_only is True
    assert args.limit == 10


def test_build_parser_select_only():
    """--select-only 标志可解析。"""
    parser = build_parser()
    args = parser.parse_args(["--select-only"])
    assert args.select_only is True


def test_build_parser_no_publish():
    """--no-publish 标志可解析。"""
    parser = build_parser()
    args = parser.parse_args(["--no-publish"])
    assert args.no_publish is True


def test_run_check_config_returns_zero(project_dir: Path, capsys: pytest.CaptureFixture):
    """--check-config 加载配置成功,返回 0,输出源数量与分类列表。"""
    exit_code = run_check_config(project_dir)
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "ai-research" in captured.out
    assert "1" in captured.out  # 1 个源


def test_run_check_config_missing_config(tmp_path: Path, capsys: pytest.CaptureFixture):
    """--check-config 无 config.json 时返回非零。"""
    exit_code = run_check_config(tmp_path)
    assert exit_code != 0


def test_main_classify_only_dispatches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """main() 收到 --classify-only 时分发到 run_classify_only(通过 spy 验证调用,非 mock LLM)。"""
    from src import main as main_mod

    called: dict = {}

    async def fake_run(project_dir, hours, limit):
        called["args"] = (project_dir, hours, limit)
        return 0

    monkeypatch.setattr(main_mod, "run_classify_only", fake_run)
    monkeypatch.setattr(main_mod, "load_dotenv", lambda **kw: None)
    exit_code = main_mod.main(["--classify-only", "--hours", "12", "--limit", "5"])
    assert exit_code == 0
    assert called["args"][1] == 12
    assert called["args"][2] == 5


def test_main_select_only_dispatches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """main() 收到 --select-only 时分发到 run_select_only(通过 spy 验证调用,非 mock LLM)。"""
    from src import main as main_mod

    called: dict = {}

    async def fake_run(project_dir, hours, limit):
        called["args"] = (project_dir, hours, limit)
        return 0

    monkeypatch.setattr(main_mod, "run_select_only", fake_run)
    monkeypatch.setattr(main_mod, "load_dotenv", lambda **kw: None)
    exit_code = main_mod.main(["--select-only", "--hours", "24"])
    assert exit_code == 0
    assert called["args"][1] == 24


def test_main_analyze_one_dispatches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """main() 收到 --analyze-one 时分发到 run_analyze_one(通过 spy 验证调用,非 mock LLM)。"""
    from src import main as main_mod

    called: dict = {}

    async def fake_run(project_dir, hours, item_id):
        called["args"] = (project_dir, hours, item_id)
        return 0

    monkeypatch.setattr(main_mod, "run_analyze_one", fake_run)
    monkeypatch.setattr(main_mod, "load_dotenv", lambda **kw: None)
    exit_code = main_mod.main(["--analyze-one", "rss_test_abc", "--hours", "24"])
    assert exit_code == 0
    assert called["args"][1] == 24
    assert called["args"][2] == "rss_test_abc"


def test_main_default_dispatches_to_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """main() 默认(无子命令标志)分发到 run_pipeline(通过 spy 验证,非 mock LLM)。"""
    from src import main as main_mod

    called: dict = {}

    async def fake_run(project_dir, hours, no_publish, limit):
        called["args"] = (project_dir, hours, no_publish, limit)
        return 0

    monkeypatch.setattr(main_mod, "run_pipeline", fake_run)
    monkeypatch.setattr(main_mod, "load_dotenv", lambda **kw: None)
    exit_code = main_mod.main(["--hours", "12", "--no-publish"])
    assert exit_code == 0
    assert called["args"][1] == 12
    assert called["args"][2] is True  # --no-publish


def test_main_default_no_publish_false(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """main() 默认(无 --no-publish)no_publish=False。"""
    from src import main as main_mod

    called: dict = {}

    async def fake_run(project_dir, hours, no_publish, limit):
        called["args"] = (project_dir, hours, no_publish, limit)
        return 0

    monkeypatch.setattr(main_mod, "run_pipeline", fake_run)
    monkeypatch.setattr(main_mod, "load_dotenv", lambda **kw: None)
    exit_code = main_mod.main(["--hours", "24"])
    assert exit_code == 0
    assert called["args"][2] is False  # 默认发布


@pytest.mark.network
async def test_run_fetch_only_real_hn(tmp_path: Path, capsys: pytest.CaptureFixture):
    """--fetch-only 真实抓取 HN,返回 0,输出条目数。"""
    (tmp_path / "data").mkdir()
    (tmp_path / "categories").mkdir()
    (tmp_path / "feeds").mkdir()
    (tmp_path / "data" / "config.json").write_text(
        json.dumps(
            {
                "ai": {"provider": "openai", "model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY"},
                "rsshub_base_url": None,
                "categories": {
                    "dev-community": {
                        "enabled": True,
                        "display_name": {"en": "Dev", "zh": "开发者"},
                        "threshold": 5.0,
                        "digest_limit": 5,
                        "children": ["forums"],
                    }
                },
                "outputs": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "categories" / "dev-community").mkdir()
    (tmp_path / "categories" / "dev-community" / "category.json").write_text(
        json.dumps(
            {
                "enabled": True,
                "display_name": {"en": "Dev", "zh": "开发者"},
                "threshold": 5.0,
                "digest_limit": 5,
                "children": ["forums"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "feeds" / "dev-community.yml").write_text(
        "- name: Hacker News\n"
        "  url: https://hnrss.org/frontpage\n"
        "  category: dev-community/forums\n",
        encoding="utf-8",
    )
    exit_code = await run_fetch_only(tmp_path, hours=24)
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Hacker News" in captured.out
