"""Source 层抽象:Source Protocol 定义信息源契约,RSSSource 为主要实现。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.models import ContentItem


@runtime_checkable
class Source(Protocol):
    """信息源协议:只读产出 ContentItem 列表,无状态,无写回。

    RSS feed 本身即消息队列:fetch 返回 feed 当前全部条目(不按时间过滤),
    已处理与否由 DedupStore 判定(断点续传),未处理条目下次运行继续消费。
    扩展点:未来非 RSS 源(如 B站未公开 API)可实现此 Protocol。
    """

    category: str

    async def fetch(self) -> list[ContentItem]:
        """拉取 feed 当前全部条目。单源失败应返回空列表,不抛异常。"""
        ...
