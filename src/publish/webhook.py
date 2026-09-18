"""Webhook 发布:飞书/钉钉/Slack/Discord/自定义,单 webhook 失败不中断其他。

每种 webhook 类型有独立的 payload 格式,统一通过 httpx POST 发布。
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)


class WebhookType(str, Enum):
    """Webhook 类型:feishu/slack/discord/custom。"""

    FEISHU = "feishu"
    SLACK = "slack"
    DISCORD = "discord"
    CUSTOM = "custom"


class _Webhook(Protocol):
    """Webhook 协议:build_payload + url。"""

    url: str

    def build_payload(self, content: str) -> dict[str, Any]: ...


class FeishuWebhook:
    """飞书/Lark webhook:msg_type=text,content.text=payload。"""

    def __init__(self, url: str) -> None:
        self.url = url

    def build_payload(self, content: str) -> dict[str, Any]:
        return {"msg_type": "text", "content": {"text": content}}


class SlackWebhook:
    """Slack webhook:text=payload。"""

    def __init__(self, url: str) -> None:
        self.url = url

    def build_payload(self, content: str) -> dict[str, Any]:
        return {"text": content}


class DiscordWebhook:
    """Discord webhook:content=payload。"""

    def __init__(self, url: str) -> None:
        self.url = url

    def build_payload(self, content: str) -> dict[str, Any]:
        return {"content": content}


class CustomWebhook:
    """自定义 webhook:直接 POST 原始 content 作为 JSON。"""

    def __init__(self, url: str) -> None:
        self.url = url

    def build_payload(self, content: str) -> dict[str, Any]:
        return {"content": content}


_TYPE_MAP: dict[str, type] = {
    WebhookType.FEISHU.value: FeishuWebhook,
    WebhookType.SLACK.value: SlackWebhook,
    WebhookType.DISCORD.value: DiscordWebhook,
    WebhookType.CUSTOM.value: CustomWebhook,
}


class WebhookPublisher:
    """Webhook 发布器:多 webhook 发布,单 webhook 失败不中断。

    示例:
        publisher = WebhookPublisher([{"type": "feishu", "url": "..."}])
        await publisher.publish(content=md, date=datetime.now())
    """

    def __init__(self, configs: list[dict[str, Any]]):
        """从配置列表构造 webhook,跳过未知类型与缺 url 的配置。"""
        self.webhooks: list[_Webhook] = []
        for cfg in configs:
            url = cfg.get("url")
            if not url:
                logger.debug("Skipping webhook config without url: %s", cfg)
                continue
            cls = _TYPE_MAP.get(cfg.get("type", ""))
            if cls is None:
                logger.debug("Skipping webhook with unknown type: %s", cfg.get("type"))
                continue
            self.webhooks.append(cls(url))

    async def publish(self, content: str, date: datetime) -> list[tuple[bool, str | None]]:
        """并发向所有 webhook 发布简报,返回 [(success, error), ...]。单 webhook 失败不中断。"""
        import asyncio

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            results = await asyncio.gather(
                *(self._publish_one(client, webhook, content, date) for webhook in self.webhooks)
            )
        return list(results)

    async def _publish_one(
        self,
        client: httpx.AsyncClient,
        webhook: _Webhook,
        content: str,
        date: datetime,
    ) -> tuple[bool, str | None]:
        """发布到单个 webhook,失败返回 (False, error_msg)。"""
        payload = webhook.build_payload(content)
        try:
            response = await client.post(webhook.url, json=payload)
            response.raise_for_status()
            return True, None
        except httpx.HTTPError as e:
            msg = str(e) or f"{type(e).__name__} for {webhook.url}"
            logger.warning("Webhook %s failed: %s", webhook.url, msg)
            return False, msg
        except Exception as e:
            msg = str(e) or f"{type(e).__name__} for {webhook.url}"
            logger.warning("Webhook %s error: %s", webhook.url, msg)
            return False, msg
