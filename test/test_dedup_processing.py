"""跨源 URL 去重 + 分类分组测试:纯逻辑,无网络无 LLM。"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.models import ContentAnalysis, ContentItem, ItemProcessing, SourceType
from src.processing.dedup import dedup_by_url, group_by_category


def _make_item(
    item_id: str,
    url: str,
    title: str = "标题",
    category_path: str = "ai-research/ai-papers",
    score: float = 7.0,
) -> ContentItem:
    """构造带 analysis 的测试 ContentItem。"""
    return ContentItem(
        id=item_id,
        source_type=SourceType.RSS,
        title=title,
        url=url,
        content="内容",
        author="作者",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        processing=ItemProcessing(
            analysis=ContentAnalysis(
                category_path=category_path,
                score=score,
                summary="摘要",
                tags=[],
            )
        ),
    )


def test_dedup_by_url_merges_same_normalized_url():
    """同 URL 不同追踪参数 → 合并为 1 条,保留分数最高的。"""
    items = [
        _make_item("a", "https://example.com/post?utm_source=x", score=7.0),
        _make_item("b", "https://example.com/post?utm_source=y", score=8.5),
    ]
    result = dedup_by_url(items)
    assert len(result) == 1
    assert result[0].processing.analysis.score == 8.5  # 保留高分


def test_dedup_by_url_preserves_different_urls():
    """不同 URL 保留。"""
    items = [
        _make_item("a", "https://example.com/post1"),
        _make_item("b", "https://example.com/post2"),
    ]
    result = dedup_by_url(items)
    assert len(result) == 2


def test_dedup_by_url_fragment_treated_same():
    """fragment 差异视作同一 URL。"""
    items = [
        _make_item("a", "https://example.com/post#section1"),
        _make_item("b", "https://example.com/post#section2"),
    ]
    result = dedup_by_url(items)
    assert len(result) == 1


def test_dedup_by_url_http_https_treated_same():
    """http 与 https 视作同一 URL。"""
    items = [
        _make_item("a", "http://example.com/post"),
        _make_item("b", "https://example.com/post"),
    ]
    result = dedup_by_url(items)
    assert len(result) == 1


def test_dedup_by_url_empty_list():
    """空列表返回空。"""
    assert dedup_by_url([]) == []


def test_dedup_by_url_keeps_highest_score():
    """同 URL 多条,保留分数最高的(即使不在首位)。"""
    items = [
        _make_item("a", "https://example.com/p", score=5.0),
        _make_item("b", "https://example.com/p", score=9.5),
        _make_item("c", "https://example.com/p", score=7.0),
    ]
    result = dedup_by_url(items)
    assert len(result) == 1
    assert result[0].processing.analysis.score == 9.5


def test_dedup_by_url_no_analysis_kept():
    """无 analysis 的条目 score 视作 0,但 URL 不同时仍保留。"""
    item_no_analysis = ContentItem(
        id="x",
        source_type=SourceType.RSS,
        title="无分析",
        url="https://example.com/unique",
        content="",
        author="",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        processing=None,
    )
    items = [item_no_analysis, _make_item("y", "https://example.com/other", score=7.0)]
    result = dedup_by_url(items)
    assert len(result) == 2


def test_group_by_category_groups_by_analysis_path():
    """按 analysis.category_path 分组。"""
    items = [
        _make_item("a", "https://x.com/1", category_path="ai-research/ai-papers"),
        _make_item("b", "https://x.com/2", category_path="ai-research/ai-vendor"),
        _make_item("c", "https://x.com/3", category_path="systems/eng-blog"),
    ]
    grouped = group_by_category(items)
    assert "ai-research/ai-papers" in grouped
    assert "ai-research/ai-vendor" in grouped
    assert "systems/eng-blog" in grouped
    assert len(grouped["ai-research/ai-papers"]) == 1


def test_group_by_category_by_parent_prefix():
    """按父分类前缀分组(group_by_parent=True 时)。"""
    items = [
        _make_item("a", "https://x.com/1", category_path="ai-research/ai-papers"),
        _make_item("b", "https://x.com/2", category_path="ai-research/ai-vendor"),
        _make_item("c", "https://x.com/3", category_path="systems/eng-blog"),
    ]
    grouped = group_by_category(items, by_parent=True)
    assert "ai-research" in grouped
    assert "systems" in grouped
    assert len(grouped["ai-research"]) == 2
    assert len(grouped["systems"]) == 1


def test_group_by_category_empty():
    """空列表返回空 dict。"""
    assert group_by_category([]) == {}


def test_group_by_category_no_analysis_skipped():
    """无 analysis 的条目被跳过(无分类路径)。"""
    item_no_analysis = ContentItem(
        id="x",
        source_type=SourceType.RSS,
        title="无分析",
        url="https://example.com/unique",
        content="",
        author="",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        processing=None,
    )
    items = [item_no_analysis, _make_item("y", "https://x.com/2", category_path="ai-research/ai-papers")]
    grouped = group_by_category(items)
    assert "ai-research/ai-papers" in grouped
    assert len(grouped["ai-research/ai-papers"]) == 1
