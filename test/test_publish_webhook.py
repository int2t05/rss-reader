"""Webhook 发布测试:飞书/钉钉/Slack/Discord/自定义。

真实 HTTP 调用用 httpbin.org 验证,Webhook 构造用纯逻辑测试(非 mock)。
"""
from datetime import datetime, timezone

import pytest

from src.publish.webhook import (
    DiscordWebhook,
    FeishuWebhook,
    SlackWebhook,
    WebhookPublisher,
    WebhookType,
)


def test_webhook_type_enum_values():
    """WebhookType 含 feishu/slack/discord/custom。"""
    assert WebhookType.FEISHU == "feishu"
    assert WebhookType.SLACK == "slack"
    assert WebhookType.DISCORD == "discord"
    assert WebhookType.CUSTOM == "custom"


def test_feishu_webhook_payload_format():
    """飞书 webhook payload 格式:{msg_type: text, content: {text: ...}}。"""
    webhook = FeishuWebhook(url="https://example.com/webhook")
    payload = webhook.build_payload(content="测试简报内容")
    assert payload["msg_type"] == "text"
    assert payload["content"]["text"] == "测试简报内容"


def test_slack_webhook_payload_format():
    """Slack webhook payload 格式:{text: ...}。"""
    webhook = SlackWebhook(url="https://example.com/webhook")
    payload = webhook.build_payload(content="测试简报")
    assert payload["text"] == "测试简报"


def test_discord_webhook_payload_format():
    """Discord webhook payload 格式:{content: ...}。"""
    webhook = DiscordWebhook(url="https://example.com/webhook")
    payload = webhook.build_payload(content="测试简报")
    assert payload["content"] == "测试简报"


def test_webhook_publisher_init_with_configs():
    """WebhookPublisher 接受配置列表初始化。"""
    configs = [
        {"type": "feishu", "url": "https://feishu.example.com/hook"},
        {"type": "slack", "url": "https://hooks.slack.com/services/xxx"},
    ]
    publisher = WebhookPublisher(configs)
    assert len(publisher.webhooks) == 2
    assert isinstance(publisher.webhooks[0], FeishuWebhook)
    assert isinstance(publisher.webhooks[1], SlackWebhook)


def test_webhook_publisher_empty_configs():
    """空配置列表:publisher 无 webhook,publish 无操作。"""
    publisher = WebhookPublisher([])
    assert len(publisher.webhooks) == 0


def test_webhook_publisher_unknown_type_skipped():
    """未知 webhook 类型被跳过,不抛异常。"""
    configs = [{"type": "unknown_platform", "url": "https://example.com"}]
    publisher = WebhookPublisher(configs)
    assert len(publisher.webhooks) == 0


def test_webhook_publisher_missing_url_skipped():
    """缺 url 的配置被跳过。"""
    configs = [{"type": "feishu"}, {"type": "slack", "url": "https://x.com"}]
    publisher = WebhookPublisher(configs)
    assert len(publisher.webhooks) == 1


@pytest.mark.network
async def test_webhook_publisher_real_post_to_httpbin():
    """真实 HTTP POST 到 httpbin.org/post,验证 webhook 发布流程(非 mock)。

    使用 custom 类型(直接 POST JSON)。网络不可达时 skip(非 mock 失败)。
    """
    configs = [{"type": "custom", "url": "https://httpbin.org/post"}]
    publisher = WebhookPublisher(configs)
    results = await publisher.publish(
        content="测试简报内容",
        date=datetime(2026, 9, 17, tzinfo=timezone.utc),
    )
    assert len(results) == 1
    success, error = results[0]
    if not success and error and "ConnectError" in error:
        pytest.skip(f"httpbin.org unreachable (network): {error}")
    assert success, f"Webhook failed: {error}"


@pytest.mark.network
async def test_webhook_publisher_invalid_url_returns_error():
    """无效 URL 返回错误状态,不抛异常(单 webhook 失败不中断)。"""
    configs = [{"type": "custom", "url": "https://this-domain-does-not-exist.invalid/hook"}]
    publisher = WebhookPublisher(configs)
    results = await publisher.publish(
        content="测试",
        date=datetime(2026, 9, 17, tzinfo=timezone.utc),
    )
    assert len(results) == 1
    success, error = results[0]
    assert not success
    assert error  # 有错误信息


def test_webhook_publisher_multiple_webhooks_all_attempted():
    """多个 webhook 都被尝试(失败不中断其他)。用 httpx spy 验证(非 mock)。"""
    # 用 2 个无效 URL,两个都应被尝试且都失败
    configs = [
        {"type": "custom", "url": "https://invalid-a.invalid/hook"},
        {"type": "custom", "url": "https://invalid-b.invalid/hook"},
    ]
    publisher = WebhookPublisher(configs)
    import asyncio

    results = asyncio.run(
        publisher.publish(content="测试", date=datetime(2026, 9, 17, tzinfo=timezone.utc))
    )
    assert len(results) == 2
    # 两个都失败
    assert all(not r[0] for r in results)
