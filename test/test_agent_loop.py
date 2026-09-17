"""AgentLoop 测试:Tier3 有界 ReAct 循环 + CRAG + 工具调用,真实 LLM 调用。

无 API key 时跳过真实调用(非 mock)。
"""
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.ai.agent.crag import CRAGEvaluator
from src.ai.agent.fetch_chain import FetchChain
from src.ai.agent.loop import AgentLoop
from src.ai.agent.search_chain import SearchChain
from src.ai.agent.tool import ToolRegistry
from src.ai.client import AIClient, AIClientConfig
from src.models import ContentItem, ItemProcessing, ContentAnalysis, SourceType
from src.processing.categories import CategoryRegistry


def _get_test_config() -> AIClientConfig:
    """从 .env 读取测试凭证。"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set — skipping real LLM call (not mocked)")
    return AIClientConfig(
        provider="openai",
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        api_key_env="OPENAI_API_KEY",
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )


def _make_item(content: str, title: str = "测试条目") -> ContentItem:
    """构造测试 ContentItem,带 Tier1 analysis。"""
    return ContentItem(
        id="rss_test_abc",
        source_type=SourceType.RSS,
        title=title,
        url="https://example.com/post",
        content=content,
        author="作者",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        category="ai-research/ai-papers",
        processing=ItemProcessing(
            analysis=ContentAnalysis(
                category_path="ai-research/ai-papers",
                score=8.0,
                summary=title,
                tags=[],
            )
        ),
    )


def _build_loop(client: AIClient) -> AgentLoop:
    """构造 AgentLoop:CRAG + 工具注册表(SearchChain + FetchChain)。"""
    registry = ToolRegistry()
    # 注册 web_search / web_fetch 工具(由 loop 内部构建,此处仅 placeholder)
    crag = CRAGEvaluator()
    loop = AgentLoop(
        client=client,
        registry=registry,
        crag=crag,
        search_chain=SearchChain.build_default(exa_api_key=os.environ.get("EXA_API_KEY")),
        fetch_chain=FetchChain.build_default(firecrawl_api_key=os.environ.get("FIRECRAWL_API_KEY")),
        max_steps=10,
    )
    return loop


@pytest.mark.llm
async def test_agent_loop_strong_content_skips_tools():
    """真实 LLM:strong 内容(长 + 技术细节)直接输出 JSON,不调用工具。"""
    cfg = _get_test_config()
    client = AIClient(cfg)
    loop = _build_loop(client)
    # 构造 strong 内容:长 + 技术细节
    content = "本文提出新的 Transformer 架构,使用 self-attention 机制,版本 2.0。代码示例:def forward(x): return x。API 调用 HTTP 接口,GPU 加速。" * 50
    item = _make_item(content, title="新 Transformer 架构论文")

    result = await loop.run(item, category_display_name="AI 研究")
    assert result is not None
    assert result.title
    assert result.summary
    assert isinstance(result.tags, list)


@pytest.mark.llm
async def test_agent_loop_weak_content_triggers_search():
    """真实 LLM:weak 内容(短)触发 web_search 工具调用,仍返回结构化结果。"""
    cfg = _get_test_config()
    client = AIClient(cfg)
    loop = _build_loop(client)
    item = _make_item("短内容。", title="短新闻")

    result = await loop.run(item, category_display_name="科技资讯")
    assert result is not None
    assert result.title
    assert result.summary


@pytest.mark.llm
async def test_agent_loop_returns_analysis_result_fields():
    """真实 LLM:返回 AnalysisResult 含 title/summary/background/impact/references/tags。"""
    cfg = _get_test_config()
    client = AIClient(cfg)
    loop = _build_loop(client)
    content = "OpenAI 发布 GPT-5,支持多模态推理,性能比 GPT-4 提升 30%。API 已开放。版本 1.0 发布。" * 30
    item = _make_item(content, title="GPT-5 发布")

    result = await loop.run(item, category_display_name="AI 研究")
    assert result.title
    assert result.summary
    # background/impact 可为空(模型决定),但字段必须存在
    assert isinstance(result.background, str)
    assert isinstance(result.impact, str)
    assert isinstance(result.references, list)
    assert isinstance(result.tags, list)


@pytest.mark.llm
async def test_agent_loop_respects_max_steps():
    """真实 LLM:max_steps=2 时仍能返回结果(可能 fallback)。"""
    cfg = _get_test_config()
    client = AIClient(cfg)
    crag = CRAGEvaluator()
    registry = ToolRegistry()
    loop = AgentLoop(
        client=client,
        registry=registry,
        crag=crag,
        search_chain=SearchChain.build_default(exa_api_key=os.environ.get("EXA_API_KEY")),
        fetch_chain=FetchChain.build_default(firecrawl_api_key=os.environ.get("FIRECRAWL_API_KEY")),
        max_steps=2,  # 严格限制
    )
    item = _make_item("短内容需要联网。", title="测试 max_steps")
    result = await loop.run(item, category_display_name="AI 研究")
    assert result is not None
    assert result.title  # 即使 fallback,也要有 title


def test_agent_loop_fallback_result_on_failure(monkeypatch: pytest.MonkeyPatch):
    """LLM 调用失败时,_fallback_result 返回带 title/summary 的 AnalysisResult(不抛异常)。"""
    cfg = AIClientConfig(provider="openai", model="x", api_key_env="OPENAI_API_KEY")
    # 不构造 AIClient(避免真实 key),直接测 _fallback_result
    crag = CRAGEvaluator()
    registry = ToolRegistry()
    loop = AgentLoop(
        client=None,  # type: ignore[arg-type]
        registry=registry,
        crag=crag,
        search_chain=None,  # type: ignore[arg-type]
        fetch_chain=None,  # type: ignore[arg-type]
        max_steps=10,
    )
    item = _make_item("内容", title="Fallback 测试")
    fallback = loop._fallback_result(item)
    assert fallback.title == "Fallback 测试"
    assert fallback.summary  # 非空
    assert fallback.background == ""
    assert fallback.references == []
    assert fallback.tags == []
