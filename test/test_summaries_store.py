"""总结落盘测试:Markdown 写入 data/summaries/YYYY-MM-DD.md,真实文件 I/O。"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.storage.summaries import SummaryStore


@pytest.fixture
def store(tmp_path: Path) -> SummaryStore:
    """临时 summaries 目录的 SummaryStore。"""
    return SummaryStore(tmp_path / "summaries")


def test_save_summary_creates_file(store: SummaryStore):
    """save 写入 Markdown 到 data/summaries/YYYY-MM-DD.md。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    store.save(content="# 简报\n\n内容", date=date)
    file_path = store.summaries_dir / "2026-09-17.md"
    assert file_path.exists()
    assert "# 简报" in file_path.read_text(encoding="utf-8")


def test_save_summary_bilingual_creates_two_files(store: SummaryStore):
    """save_bilingual 写入中英两份文件:YYYY-MM-DD-zh.md + YYYY-MM-DD-en.md。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    store.save_bilingual(zh="# 中文简报", en="# English Briefing", date=date)
    assert (store.summaries_dir / "2026-09-17-zh.md").exists()
    assert (store.summaries_dir / "2026-09-17-en.md").exists()
    assert "中文简报" in (store.summaries_dir / "2026-09-17-zh.md").read_text(encoding="utf-8")
    assert "English Briefing" in (store.summaries_dir / "2026-09-17-en.md").read_text(encoding="utf-8")


def test_load_summary_returns_content(store: SummaryStore):
    """load 返回已保存的 Markdown 内容。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    store.save(content="# 简报内容", date=date)
    loaded = store.load(date)
    assert loaded is not None
    assert "# 简报内容" in loaded


def test_load_summary_returns_none_if_not_exists(store: SummaryStore):
    """未保存的日期返回 None。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    assert store.load(date) is None


def test_summary_path_returns_path(store: SummaryStore):
    """summary_path 返回 YYYY-MM-DD.md 的完整路径。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    path = store.summary_path(date)
    assert path.name == "2026-09-17.md"
    assert str(store.summaries_dir) in str(path)


def test_summary_path_bilingual(store: SummaryStore):
    """summary_path 支持 lang 参数:zh/en 后缀。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    zh_path = store.summary_path(date, lang="zh")
    en_path = store.summary_path(date, lang="en")
    assert zh_path.name == "2026-09-17-zh.md"
    assert en_path.name == "2026-09-17-en.md"


def test_save_overwrites_existing(store: SummaryStore):
    """重复保存同一日期:覆盖旧内容。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    store.save(content="旧内容", date=date)
    store.save(content="新内容", date=date)
    loaded = store.load(date)
    assert "新内容" in loaded
    assert "旧内容" not in loaded


def test_store_creates_dir_if_not_exists(tmp_path: Path):
    """目录不存在时自动创建。"""
    summaries_dir = tmp_path / "new" / "summaries"
    store = SummaryStore(summaries_dir)
    assert not summaries_dir.exists()
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    store.save(content="内容", date=date)
    assert summaries_dir.exists()
    assert (summaries_dir / "2026-09-17.md").exists()


def test_list_summaries(store: SummaryStore):
    """list_summaries 返回已保存日期列表(按日期降序)。"""
    store.save(content="day1", date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    store.save(content="day2", date=datetime(2026, 9, 18, tzinfo=timezone.utc))
    store.save(content="day3", date=datetime(2026, 9, 16, tzinfo=timezone.utc))
    dates = store.list_summaries()
    assert len(dates) == 3
    # 按日期降序
    assert dates[0].day == 18
    assert dates[1].day == 17
    assert dates[2].day == 16
