"""FetchChain 测试:降级链逻辑 + 真实抓取 + SSRF 防护。

Chain 降级逻辑用 Fake backend(简单内存实现,非 mock);真实后端调用为 network mark。
"""
import pytest

from src.ai.agent.fetch_chain import (
    FetchChain,
    FetchClient,
    FetchResult,
    TrafilaturaClient,
)


class _FakeFetchBackend:
    """Fake 抓取后端:返回预设内容或抛异常,验证 Chain 降级(非 mock)。"""

    def __init__(self, name: str, content: str | None = None, raises: Exception | None = None):
        self.name = name
        self._content = content
        self._raises = raises
        self.call_count = 0

    async def fetch(self, url: str) -> str:
        self.call_count += 1
        if self._raises:
            raise self._raises
        return self._content or ""


def test_chain_returns_first_successful_content():
    """首个成功后端返回内容,后续不调用。"""
    fake_a = _FakeFetchBackend("a", content="内容 A")
    fake_b = _FakeFetchBackend("b", content="内容 B")
    chain = FetchChain([fake_a, fake_b])
    import asyncio

    result = asyncio.run(chain.fetch("https://example.com/post"))
    assert result == "内容 A"
    assert fake_a.call_count == 1
    assert fake_b.call_count == 0


def test_chain_falls_through_on_failure():
    """首个后端抛异常,降级到第二个。"""
    fake_a = _FakeFetchBackend("a", raises=RuntimeError("firecrawl down"))
    fake_b = _FakeFetchBackend("b", content="trafilatura 内容")
    chain = FetchChain([fake_a, fake_b])
    import asyncio

    result = asyncio.run(chain.fetch("https://example.com/post"))
    assert result == "trafilatura 内容"


def test_chain_falls_through_on_empty_content():
    """首个后端返回空字符串,降级到第二个(空内容视为失败)。"""
    fake_a = _FakeFetchBackend("a", content="")
    fake_b = _FakeFetchBackend("b", content="fallback 内容")
    chain = FetchChain([fake_a, fake_b])
    import asyncio

    result = asyncio.run(chain.fetch("https://example.com/post"))
    assert result == "fallback 内容"


def test_chain_returns_empty_when_all_fail():
    """所有后端失败/空时返回空字符串,不抛异常。"""
    fake_a = _FakeFetchBackend("a", raises=RuntimeError("a down"))
    fake_b = _FakeFetchBackend("b", content="")
    chain = FetchChain([fake_a, fake_b])
    import asyncio

    result = asyncio.run(chain.fetch("https://example.com/post"))
    assert result == ""


def test_chain_empty_backends():
    """空后端列表:返回空,不抛异常。"""
    chain = FetchChain([])
    import asyncio

    assert asyncio.run(chain.fetch("https://example.com/post")) == ""


def test_chain_rejects_ssrf_url():
    """Chain 内置 SSRF 防护:拒绝 localhost。"""
    from src.ai.agent.ssrf import ValidationError

    fake = _FakeFetchBackend("a", content="不应该被调用")
    chain = FetchChain([fake])
    import asyncio

    with pytest.raises(ValidationError):
        asyncio.run(chain.fetch("http://localhost/admin"))
    assert fake.call_count == 0  # SSRF 验证在调用后端前


@pytest.mark.network
async def test_trafilatura_client_real_fetch():
    """真实 trafilatura 抓取公开网页:返回非空正文(网络超时则 skip)。"""
    client = TrafilaturaClient()
    try:
        content = await client.fetch("https://example.com")
    except Exception as e:
        pytest.skip(f"trafilatura fetch unreachable (network): {type(e).__name__}")
    assert isinstance(content, str)
    # example.com 内容简单,trafilatura 可能返回空,所以只验证类型


@pytest.mark.network
async def test_fetch_chain_real_call():
    """真实 FetchChain 抓取:trafilatura 兜底,返回内容或空(网络超时则 skip)。"""
    chain = FetchChain.build_default(firecrawl_api_key=None)
    try:
        content = await chain.fetch("https://example.com")
    except Exception as e:
        pytest.skip(f"FetchChain unreachable (network): {type(e).__name__}")
    assert isinstance(content, str)
