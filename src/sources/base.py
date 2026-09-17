"""Source 层抽象:Source Protocol 定义信息源契约,RSSSource 为主要实现。"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from src.models import ContentItem


@runtime_checkable
class Source(Protocol):
    """信息源协议:只读产出 ContentItem 列表,无状态,无写回。

    扩展点:未来非 RSS 源(如 B站未公开 API)可实现此 Protocol。
    当前所有源走 RSS,RSSSource 是此 Protocol 的唯一实现。
    """

    category: str

    async def fetch(self, since: datetime) -> list[ContentItem]:
        """拉取 since 之后的新条目。单源失败应返回空列表,不抛异常。"""
        ...
