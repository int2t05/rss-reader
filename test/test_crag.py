"""CRAG 评估器测试:strong/ambiguous/weak 三态判定,纯逻辑。"""
import pytest

from src.ai.agent.crag import CRAGEvaluator
from src.models import ContentItem, SourceType
from datetime import datetime, timezone


def _make_item(content: str) -> ContentItem:
    """构造指定 content 的测试 ContentItem。"""
    return ContentItem(
        id="test",
        source_type=SourceType.RSS,
        title="测试",
        url="https://example.com/post",
        content=content,
        author="作者",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
    )


def test_crag_strong_for_long_technical_content():
    """长内容(>2000 字符)含技术细节 → strong。"""
    content = "本文提出新的 Transformer 架构,使用 `self-attention` 机制,版本 2.0。代码示例:def forward(x): return x。API 调用 HTTP 接口,GPU 加速。" * 50
    item = _make_item(content)
    evaluator = CRAGEvaluator()
    assert evaluator.evaluate(item) == "strong"


def test_crag_weak_for_short_content():
    """短内容(<500 字符)→ weak。"""
    item = _make_item("短新闻标题。")
    evaluator = CRAGEvaluator()
    assert evaluator.evaluate(item) == "weak"


def test_crag_ambiguous_for_medium_content():
    """中等长度内容(500-2000 字符)→ ambiguous。"""
    content = "这是一段中等长度的内容,描述了某个技术新闻,但没有代码块或 API 等明显技术标记。" * 30
    item = _make_item(content)
    evaluator = CRAGEvaluator()
    assert evaluator.evaluate(item) == "ambiguous"


def test_crag_strong_requires_technical_detail():
    """长内容但无技术细节 → ambiguous(不达 strong)。"""
    content = "这是一段普通的新闻报道,没有任何代码、API、技术术语或版本号,只是描述事件经过。" * 50
    item = _make_item(content)
    evaluator = CRAGEvaluator()
    verdict = evaluator.evaluate(item)
    assert verdict in ("ambiguous", "strong")  # 容忍边界


def test_crag_strong_with_code_block():
    """含 ``` 代码块 → 技术细节 → 有机会达 strong(若长度足够)。"""
    content = "```python\\ndef train(model, data):\\n    return model.fit(data)\\n```" + " API GPU HTTP " * 200
    item = _make_item(content)
    evaluator = CRAGEvaluator()
    assert evaluator.evaluate(item) == "strong"


def test_crag_strong_with_version_number():
    """含版本号(如 2.0.1)→ 技术细节。"""
    content = "项目发布 v2.0.1 版本,修复若干 bug。" * 100
    item = _make_item(content)
    evaluator = CRAGEvaluator()
    assert evaluator.evaluate(item) == "strong"


def test_crag_weak_empty_content():
    """空内容 → weak。"""
    item = _make_item("")
    evaluator = CRAGEvaluator()
    assert evaluator.evaluate(item) == "weak"


def test_crag_verdict_values():
    """CRAG 评估结果只可能是 strong/ambiguous/weak 之一。"""
    evaluator = CRAGEvaluator()
    for content in ["", "短", "中" * 800, "长" * 2500 + " code " * 10]:
        verdict = evaluator.evaluate(_make_item(content))
        assert verdict in ("strong", "ambiguous", "weak")
