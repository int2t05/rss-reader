"""SQLite 去重状态测试:真实 SQLite 操作,无 mock。"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.storage.dedup import DedupStore


@pytest.fixture
def store(tmp_path: Path) -> DedupStore:
    """临时 SQLite 文件的 DedupStore。"""
    return DedupStore(tmp_path / "dedup.db")


def test_new_item_not_processed(store: DedupStore):
    """未处理过的 item_id 返回 False。"""
    assert store.is_processed("rss_test_abc") is False


def test_mark_processed_then_is_processed(store: DedupStore):
    """标记后 is_processed 返回 True。"""
    store.mark_processed("rss_test_abc")
    assert store.is_processed("rss_test_abc") is True


def test_mark_processed_idempotent(store: DedupStore):
    """重复标记幂等:多次 mark_processed 不报错,结果一致。"""
    store.mark_processed("rss_test_abc")
    store.mark_processed("rss_test_abc")  # 幂等
    assert store.is_processed("rss_test_abc") is True


def test_persistence_across_reopen(tmp_path: Path):
    """DedupStore 重开后,已处理的 item_id 仍然存在。"""
    store1 = DedupStore(tmp_path / "dedup.db")
    store1.mark_processed("rss_test_persist")
    store1.close()

    store2 = DedupStore(tmp_path / "dedup.db")
    assert store2.is_processed("rss_test_persist") is True
    store2.close()


def test_batch_is_processed(store: DedupStore):
    """批量查询:返回未处理的 item_id 列表。"""
    store.mark_processed("a")
    store.mark_processed("b")
    unprocessed = store.batch_unprocessed(["a", "b", "c", "d"])
    assert unprocessed == ["c", "d"]


def test_get_processed_at(store: DedupStore):
    """mark_processed 时记录 fetched_at 时间戳,get_processed_at 返回 datetime。"""
    before = datetime.now(timezone.utc)
    store.mark_processed("rss_with_ts")
    after = datetime.now(timezone.utc)

    ts = store.get_processed_at("rss_with_ts")
    assert ts is not None
    assert before <= ts <= after


def test_get_processed_at_returns_none_for_unknown(store: DedupStore):
    """未处理的 item_id 返回 None。"""
    assert store.get_processed_at("never_seen") is None


def test_clear_all(store: DedupStore):
    """清空去重表,用于 re-run 场景。"""
    store.mark_processed("a")
    store.mark_processed("b")
    store.clear()
    assert store.is_processed("a") is False
    assert store.is_processed("b") is False


def test_context_manager(tmp_path: Path):
    """DedupStore 支持 with 语法,自动 close。"""
    with DedupStore(tmp_path / "dedup.db") as store:
        store.mark_processed("x")
        assert store.is_processed("x") is True
