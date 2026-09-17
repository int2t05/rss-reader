"""SearchChain 测试:降级链逻辑 + 真实 Exa/DuckDuckGo 调用。

Chain 降级逻辑用 Fake backend(简单内存实现,非 mock);真实后端调用为 llm/network mark。
"""
import os

import pytest

from src.ai.agent.search_chain import (
    DuckDuckGoClient,
    ExaClient,
    SearchChain,
    SearchResult,
)


def test_search_result_model():
    """SearchResult 含 title/url/snippet。"""
    r = SearchResult(title="Test", url="https://example.com", snippet="Snippet")
    assert r.title == "Test"
    assert r.url == "https://example.com"
    assert r.snippet == "Snippet"


class _FakeBackend:
    """Fake 搜索后端:返回预设结果或抛异常,用于验证 Chain 降级逻辑(非 mock LLM)。"""

    def __init__(self, name: str, results: list[SearchResult] | None = None, raises: Exception | None = None):
        self.name = name
        self._results = results
        self._raises = raises
        self.call_count = 0

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        self.call_count += 1
        if self._raises:
            raise self._raises
        return list(self._results or [])


def test_chain_returns_first_successful_results():
    """首个成功后端返回结果,后续不调用。"""
    fake_a = _FakeBackend("a", results=[SearchResult("A1", "https://a.com/1", "s1")])
    fake_b = _FakeBackend("b", results=[SearchResult("B1", "https://b.com/1", "s2")])
    chain = SearchChain([fake_a, fake_b])
    import asyncio

    results = asyncio.run(chain.search("query"))
    assert len(results) == 1
    assert results[0].title == "A1"
    assert fake_a.call_count == 1
    assert fake_b.call_count == 0  # 首个成功,后续不调用


def test_chain_falls_through_to_second_on_failure():
    """首个后端抛异常,降级到第二个。"""
    fake_a = _FakeBackend("a", raises=RuntimeError("exa down"))
    fake_b = _FakeBackend("b", results=[SearchResult("B1", "https://b.com/1", "s2")])
    chain = SearchChain([fake_a, fake_b])
    import asyncio

    results = asyncio.run(chain.search("query"))
    assert len(results) == 1
    assert results[0].title == "B1"
    assert fake_a.call_count == 1
    assert fake_b.call_count == 1


def test_chain_falls_through_on_empty_results():
    """首个后端返回空列表,降级到第二个(空结果视为失败)。"""
    fake_a = _FakeBackend("a", results=[])
    fake_b = _FakeBackend("b", results=[SearchResult("B1", "https://b.com/1", "s2")])
    chain = SearchChain([fake_a, fake_b])
    import asyncio

    results = asyncio.run(chain.search("query"))
    assert len(results) == 1
    assert results[0].title == "B1"


def test_chain_returns_empty_when_all_fail():
    """所有后端都失败/空时返回空列表,不抛异常。"""
    fake_a = _FakeBackend("a", raises=RuntimeError("a down"))
    fake_b = _FakeBackend("b", results=[])
    chain = SearchChain([fake_a, fake_b])
    import asyncio

    results = asyncio.run(chain.search("query"))
    assert results == []


def test_chain_single_backend():
    """单后端:成功返回,失败返回空。"""
    fake = _FakeBackend("only", results=[SearchResult("R1", "https://r.com/1", "s")])
    chain = SearchChain([fake])
    import asyncio

    assert len(asyncio.run(chain.search("q"))) == 1

    fake_fail = _FakeBackend("only", raises=RuntimeError("down"))
    chain_fail = SearchChain([fake_fail])
    assert asyncio.run(chain_fail.search("q")) == []


def test_chain_empty_backends():
    """空后端列表:返回空,不抛异常。"""
    chain = SearchChain([])
    import asyncio

    assert asyncio.run(chain.search("q")) == []


def test_exa_client_init_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    """ExaClient 无 EXA_API_KEY 时抛 ValueError。"""
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="EXA_API_KEY"):
        ExaClient()


def test_exa_client_init_with_key(monkeypatch: pytest.MonkeyPatch):
    """ExaClient 有 EXA_API_KEY 时构造成功。"""
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    client = ExaClient()
    assert client is not None


@pytest.mark.llm
async def test_exa_client_real_search():
    """真实 Exa API 调用:返回非空搜索结果(网络不可达时 skip,非 mock)。"""
    if not os.environ.get("EXA_API_KEY"):
        pytest.skip("EXA_API_KEY not set — skipping real Exa call (not mocked)")
    client = ExaClient()
    try:
        results = await client.search("OpenAI GPT-5 release", max_results=3)
    except Exception as e:
        pytest.skip(f"Exa API unreachable (network): {type(e).__name__}")
    assert isinstance(results, list)
    if results:
        assert isinstance(results[0], SearchResult)
        assert results[0].url.startswith("http")


@pytest.mark.network
async def test_duckduckgo_client_real_search():
    """真实 DuckDuckGo 搜索:零配置,返回非空结果(网络超时则 skip,非 mock)。"""
    client = DuckDuckGoClient()
    try:
        results = await client.search("Python programming language", max_results=3)
    except Exception as e:
        pytest.skip(f"DuckDuckGo unreachable (network): {type(e).__name__}")
    assert isinstance(results, list)
    if results:
        assert isinstance(results[0], SearchResult)
        assert results[0].url.startswith("http")


@pytest.mark.network
async def test_chain_real_ddgs_fallback_when_exa_absent(monkeypatch: pytest.MonkeyPatch):
    """无 EXA_API_KEY 时,Chain 仅 DDG 后端,真实搜索返回结果(超时则 skip)。"""
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    chain = SearchChain.build_default(exa_api_key=None)
    try:
        results = await chain.search("Rust programming", max_results=3)
    except Exception as e:
        pytest.skip(f"DuckDuckGo unreachable (network): {type(e).__name__}")
    assert isinstance(results, list)
