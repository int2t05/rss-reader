"""Markdown 简报渲染测试:按分类组织,每条目含完整字段。

纯逻辑测试,无网络无 LLM。用真实 ContentItem 数据验证渲染输出。
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.models import (
    AnalysisResult,
    ContentAnalysis,
    ContentItem,
    ItemProcessing,
    Reference,
    SourceType,
)
from src.render.markdown import render_markdown


def _make_item(
    title: str = "测试标题",
    score: float = 8.0,
    category_path: str = "ai-research/ai-papers",
    summary: str = "一句话摘要",
    deep: AnalysisResult | None = None,
) -> ContentItem:
    """构造带 Tier1 + 可选 Tier3 结果的测试 ContentItem。"""
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
            deep_analysis=deep,
        ),
    )


def test_render_markdown_contains_date():
    """简报包含日期标题。"""
    items = [_make_item()]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="zh")
    assert "2026" in md
    assert "09" in md or "9" in md


def test_render_markdown_contains_category_section():
    """按分类分节:分类路径作为标题。"""
    items = [_make_item(category_path="ai-research/ai-papers")]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="zh")
    assert "ai-research" in md.lower() or "AI 研究" in md or "ai-papers" in md.lower()


def test_render_markdown_contains_item_title():
    """每条目标题出现在简报中。"""
    items = [_make_item(title="GPT-5 正式发布")]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="zh")
    assert "GPT-5 正式发布" in md


def test_render_markdown_contains_score():
    """每条目分数出现在简报中。"""
    items = [_make_item(score=8.5)]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="zh")
    assert "8.5" in md


def test_render_markdown_contains_summary():
    """每条目摘要出现在简报中。"""
    items = [_make_item(summary="一句话技术摘要")]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="zh")
    assert "一句话技术摘要" in md


def test_render_markdown_contains_deep_analysis_fields():
    """有 Tier3 结果时,简报含 background/impact/references。"""
    deep = AnalysisResult(
        title="深度标题",
        summary="深度摘要",
        background="技术背景",
        impact="影响意义",
        references=[Reference(title="参考", url="https://ref.com")],
        tags=["t1"],
    )
    items = [_make_item(deep=deep)]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="zh")
    assert "技术背景" in md
    assert "影响意义" in md
    assert "https://ref.com" in md


def test_render_markdown_handles_no_deep_analysis():
    """无 Tier3 结果时,简报仍能渲染(仅 Tier1 字段)。"""
    items = [_make_item(deep=None)]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="zh")
    assert "测试标题" in md
    assert "一句话摘要" in md


def test_render_markdown_groups_items_by_category():
    """同分类的多个条目归入同一分类节。"""
    items = [
        _make_item(title="条目A", category_path="ai-research/ai-papers"),
        _make_item(title="条目B", category_path="ai-research/ai-papers"),
        _make_item(title="条目C", category_path="systems/eng-blog"),
    ]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="zh")
    # 同分类条目应相邻出现
    idx_a = md.find("条目A")
    idx_b = md.find("条目B")
    idx_c = md.find("条目C")
    assert idx_a < idx_b  # 同分类相邻
    # C 在不同分类节
    assert idx_c != -1


def test_render_markdown_empty_items():
    """空条目列表:简报仅含标题与说明。"""
    md = render_markdown([], date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="zh")
    assert isinstance(md, str)
    assert len(md) > 0
    assert "2026" in md


def test_render_markdown_lang_zh():
    """lang=zh:简报用中文标题。"""
    items = [_make_item()]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="zh")
    assert "简报" in md or "日报" in md or "每日" in md


def test_render_markdown_lang_en():
    """lang=en:简报用英文标题。"""
    items = [_make_item()]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="en")
    assert "Briefing" in md or "Daily" in md or "Report" in md


def test_render_markdown_contains_tags():
    """条目标签出现在简报中。"""
    items = [_make_item()]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc), lang="zh")
    assert "tag1" in md
    assert "tag2" in md
