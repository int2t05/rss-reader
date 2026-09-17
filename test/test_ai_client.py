"""AIClient 测试:客户端构造 + 真实 LLM 调用(用 Claude Code 兼容 API 凭证)。

.env 加载 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL,真实调用 GLM via Volcengine。
"""
import os

import pytest

from src.ai.client import AIClient, AIClientConfig


def _get_test_config() -> AIClientConfig:
    """从 .env 读取测试凭证,构造 AIClientConfig。"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set in .env — skipping real LLM call (not mocked)")
    return AIClientConfig(
        provider="openai",
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        api_key_env="OPENAI_API_KEY",
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )


def test_client_config_defaults():
    """AIClientConfig 默认值:analysis_concurrency=5, throttle_sec=0.0。"""
    cfg = AIClientConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key_env="OPENAI_API_KEY",
    )
    assert cfg.provider == "openai"
    assert cfg.model == "gpt-4o-mini"
    assert cfg.analysis_concurrency == 5
    assert cfg.throttle_sec == 0.0
    assert cfg.base_url is None


def test_client_config_with_base_url():
    """自定义 base_url 支持 OpenAI 兼容 provider(DeepSeek/Gemini/Ollama 等)。"""
    cfg = AIClientConfig(
        provider="deepseek",
        model="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com/v1",
    )
    assert cfg.base_url == "https://api.deepseek.com/v1"


def test_client_init_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch):
    """AIClient 从 api_key_env 指定的环境变量读取 key。"""
    monkeypatch.setenv("TEST_API_KEY", "sk-test-123")
    cfg = AIClientConfig(provider="openai", model="gpt-4o-mini", api_key_env="TEST_API_KEY")
    client = AIClient(cfg)
    assert client.api_key == "sk-test-123"


def test_client_init_missing_key_raises(monkeypatch: pytest.MonkeyPatch):
    """环境变量未设置时,构造 AIClient 抛 ValueError。"""
    monkeypatch.delenv("MISSING_KEY", raising=False)
    cfg = AIClientConfig(provider="openai", model="gpt-4o-mini", api_key_env="MISSING_KEY")
    with pytest.raises(ValueError, match="MISSING_KEY"):
        AIClient(cfg)


@pytest.mark.llm
async def test_client_complete_returns_string():
    """真实 LLM 调用:complete() 返回非空字符串。"""
    cfg = _get_test_config()
    client = AIClient(cfg)
    response = await client.complete(
        system="You are a helpful assistant. Reply with exactly: OK",
        user="Say OK.",
    )
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.llm
async def test_client_complete_real_call_classifies_item():
    """真实 LLM 调用:让模型分类一条技术新闻,返回可解析 JSON。"""
    from src.ai.utils import parse_json_response

    cfg = _get_test_config()
    client = AIClient(cfg)
    system = (
        '你是技术信息分类器。输出 JSON:{"category": "...", "score": 8.5, '
        '"summary": "...", "tags": ["..."]}'
    )
    user = "标题:GPT-5 发布\n内容:OpenAI 发布 GPT-5,支持多模态推理\n来源:OpenAI News\n类别提示:ai-research/ai-vendor"
    response = await client.complete(system=system, user=user)
    parsed = parse_json_response(response)
    assert parsed is not None, f"LLM 响应无法解析为 JSON: {response[:200]}"
    assert "category" in parsed
    assert "score" in parsed
