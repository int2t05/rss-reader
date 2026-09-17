"""RSSHub 路由源:URL 以 / 开头时解析为 {rsshub_base_url}{url},无 base_url 时跳过。"""

from __future__ import annotations

import httpx

from src.models import RSSSourceConfig
from src.sources.rss import RSSSource


def build_source(
    config: RSSSourceConfig,
    rsshub_base_url: str | None,
    http_client: httpx.AsyncClient,
) -> RSSSource | None:
    """根据 url 前缀决定源类型:/ 开头走 RSSHub(需 base_url),http 开头走直链。

    RSSHub 路由但无 base_url 时返回 None(表示该源被跳过)。
    """
    if config.url.startswith("/") and not config.url.startswith("//"):
        if not rsshub_base_url:
            return None  # RSSHub 路由但未配置 base_url,跳过此源
        merged_url = f"{rsshub_base_url.rstrip('/')}{config.url}"
        merged_config = config.model_copy(update={"url": merged_url})
        return RSSSource(merged_config, http_client)
    return RSSSource(config, http_client)
