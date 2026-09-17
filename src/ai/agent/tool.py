"""Tool Protocol + ToolRegistry:统一工具接口与注册表,借鉴 Cognik tool.go/registry.go。

Tool/SyncTool 为 Protocol(类型即语义),ToolRegistry 扁平注册表按名查找。
新项目不实现 AsyncTool(批处理无需异步派发)。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class ToolInfo:
    """工具元信息:名称、描述、参数 JSON Schema。"""

    name: str
    description: str
    parameters: dict[str, Any]


@runtime_checkable
class Tool(Protocol):
    """工具协议:info() 返回元信息。所有工具(同步/异步)实现此接口。"""

    def info(self) -> ToolInfo: ...


class SyncTool(Protocol):
    """同步工具协议:call() 阻塞返回结果字符串。

    示例:
        class WebSearchTool:
            def info(self) -> ToolInfo: ...
            async def call(self, args: dict) -> str: ...
    """
    # TODO: SyncTool 全项目从未使用(工具类直接实现 info+call),应删除或重命名为 AsyncTool

    def info(self) -> ToolInfo: ...

    async def call(self, args: dict[str, Any]) -> str: ...


class ToolRegistry:
    """扁平工具注册表:按名查找/子集。

    示例:
        reg = ToolRegistry()
        reg.register(WebSearchTool())
        tool = reg.get("web_search")
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册工具,同名覆盖前者。"""
        self._tools[tool.info().name] = tool

    def get(self, name: str) -> Tool | None:
        """按名查找工具,未注册返回 None。"""
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        """返回所有已注册工具。"""
        return list(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)
