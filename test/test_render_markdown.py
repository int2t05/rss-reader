"""Markdown 简报渲染测试:按分类组织,每条目含 title/score/summary/tags。

纯逻辑测试,无网络无 LLM。用真实 ContentItem 数据验证渲染输出。
"""
from datetime import datetime, timezone

from src.models import (
    ContentAnalysis,
    ContentItem,
    ItemProcessing,
    SourceType,
)
from src.render.markdown import render_markdown


def _make_item(
    title: str = "测试标题",
    score: float = 8.0,
    category_path: str = "ai-research/ai-papers",
    summary: str = "一句话摘要",
) -> ContentItem:
    """构造带 Tier1 analysis 的测试 ContentItem。"""
    return ContentItem(
        id="rss_test_abc",
        source_type=SourceType.RSS,
        title=title,
        url="https://example.com/post",
        content="内容",
        author="作者",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        category=category_path,
        processing=ItemProcessing(
            analysis=ContentAnalysis(
                category_path=category_path,
                score=score,
                summary=summary,
                tags=["tag1", "tag2"],
            ),
        ),
    )


def test_render_markdown_contains_date():
    """简报包含日期标题。"""
    items = [_make_item()]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "2026" in md
    assert "09" in md or "9" in md


def test_render_markdown_contains_category_section():
    """按分类分节:分类路径作为标题。"""
    items = [_make_item(category_path="ai-research/ai-papers")]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "ai-research" in md.lower() or "AI 研究" in md or "ai-papers" in md.lower()


def test_render_markdown_contains_item_title():
    """每条目标题出现在简报中。"""
    items = [_make_item(title="GPT-5 正式发布")]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "GPT-5 正式发布" in md


def test_render_markdown_contains_score():
    """每条目分数出现在简报中。"""
    items = [_make_item(score=8.5)]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "8.5" in md


def test_render_markdown_contains_summary():
    """每条目摘要出现在简报中。"""
    items = [_make_item(summary="一句话技术摘要")]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "一句话技术摘要" in md


def test_render_markdown_groups_items_by_category():
    """同分类的多个条目归入同一分类节。"""
    items = [
        _make_item(title="条目A", category_path="ai-research/ai-papers"),
        _make_item(title="条目B", category_path="ai-research/ai-papers"),
        _make_item(title="条目C", category_path="systems/eng-blog"),
    ]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    idx_a = md.find("条目A")
    idx_b = md.find("条目B")
    idx_c = md.find("条目C")
    assert idx_a < idx_b  # 同分类相邻
    assert idx_c != -1


def test_render_markdown_empty_items():
    """空条目列表:简报仅含标题与说明。"""
    md = render_markdown([], date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert isinstance(md, str)
    assert len(md) > 0
    assert "2026" in md


def test_render_markdown_contains_chinese_title():
    """简报用中文标题(每日简报)。"""
    items = [_make_item()]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "简报" in md or "日报" in md or "每日" in md


def test_render_markdown_contains_tags():
    """条目标签出现在简报中。"""
    items = [_make_item()]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "tag1" in md
    assert "tag2" in md


def test_render_markdown_escapes_link_special_chars():
    """标题/URL 含 ] 或 ) 时转义,不破坏 Markdown 链接语法。"""
    items = [_make_item(title="GPT-5 (多模态) 发布 [更新]")]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "GPT-5" in md
    assert "(多模态\\)" in md
    assert "[更新\\]" in md
