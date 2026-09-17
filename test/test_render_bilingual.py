"""双语渲染测试:同一份源数据渲染中英两份简报。

纯逻辑测试,无网络无 LLM。
"""
from datetime import datetime, timezone

import pytest

from src.models import ContentAnalysis, ContentItem, ItemProcessing, SourceType
from src.render.bilingual import render_bilingual


def _make_item(title: str = "测试标题", summary: str = "摘要") -> ContentItem:
    """构造测试 ContentItem。"""
    return ContentItem(
        id="rss_test_abc",
        source_type=SourceType.RSS,
        title=title,
        url="https://example.com/post",
        content="内容",
        author="作者",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        category="ai-research/ai-papers",
        processing=ItemProcessing(
            analysis=ContentAnalysis(
                category_path="ai-research/ai-papers",
                score=8.0,
                summary=summary,
                tags=["tag1"],
            )
        ),
    )


def test_render_bilingual_returns_two_versions():
    """render_bilingual 返回中英两份 Markdown 字符串。"""
    items = [_make_item()]
    result = render_bilingual(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert hasattr(result, "zh")
    assert hasattr(result, "en")
    assert isinstance(result.zh, str)
    assert isinstance(result.en, str)
    assert len(result.zh) > 0
    assert len(result.en) > 0


def test_render_bilingual_zh_contains_chinese_title():
    """中文版包含中文标题(每日简报)。"""
    items = [_make_item()]
    result = render_bilingual(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "简报" in result.zh or "日报" in result.zh


def test_render_bilingual_en_contains_english_title():
    """英文版包含英文标题(Daily Briefing)。"""
    items = [_make_item()]
    result = render_bilingual(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "Briefing" in result.en or "Daily" in result.en


def test_render_bilingual_both_contain_item_title():
    """中英两版都包含条目标题。"""
    items = [_make_item(title="GPT-5 发布")]
    result = render_bilingual(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "GPT-5 发布" in result.zh
    assert "GPT-5 发布" in result.en


def test_render_bilingual_both_contain_score():
    """中英两版都包含分数。"""
    items = [_make_item()]
    result = render_bilingual(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "8.0" in result.zh
    assert "8.0" in result.en


def test_render_bilingual_empty_items():
    """空条目列表:两版都正常渲染。"""
    result = render_bilingual([], date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert len(result.zh) > 0
    assert len(result.en) > 0


def test_render_bilingual_both_contain_category():
    """中英两版都包含分类信息。"""
    items = [_make_item()]
    result = render_bilingual(items, date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert "ai-research" in result.zh.lower()
    assert "ai-research" in result.en.lower()
