"""Tool Protocol + ToolRegistry 测试:纯逻辑,无网络无 LLM。"""
import pytest

from src.ai.agent.tool import ToolInfo, ToolRegistry


class _FakeTool:
    """最小 Tool 实现,用于测试 Registry。"""

    def __init__(self, name: str, description: str = "fake tool"):
        self._info = ToolInfo(
            name=name,
            description=description,
            parameters={"type": "object", "properties": {}},
        )

    def info(self) -> ToolInfo:
        return self._info

    async def call(self, args: dict) -> str:
        return f"{self._info.name} called with {args}"


def test_tool_info_fields():
    """ToolInfo 含 name/description/parameters(JSON Schema)。"""
    info = ToolInfo(name="web_search", description="Search the web", parameters={"type": "object"})
    assert info.name == "web_search"
    assert info.description == "Search the web"
    assert info.parameters["type"] == "object"


def test_registry_register_and_get():
    """注册后按名查找。"""
    reg = ToolRegistry()
    tool = _FakeTool("web_search")
    reg.register(tool)
    assert reg.get("web_search") is tool


def test_registry_get_unknown_returns_none():
    """未知工具返回 None。"""
    reg = ToolRegistry()
    assert reg.get("nonexistent") is None


def test_registry_all_returns_list():
    """all() 返回所有已注册工具。"""
    reg = ToolRegistry()
    reg.register(_FakeTool("web_search"))
    reg.register(_FakeTool("web_fetch"))
    tools = reg.all()
    assert len(tools) == 2
    names = [t.info().name for t in tools]
    assert "web_search" in names
    assert "web_fetch" in names


def test_registry_len():
    """__len__ 返回工具数。"""
    reg = ToolRegistry()
    assert len(reg) == 0
    reg.register(_FakeTool("a"))
    assert len(reg) == 1
    reg.register(_FakeTool("b"))
    assert len(reg) == 2


def test_registry_overwrite_same_name():
    """同名工具后注册覆盖前者。"""
    reg = ToolRegistry()
    first = _FakeTool("tool", "first")
    second = _FakeTool("tool", "second")
    reg.register(first)
    reg.register(second)
    assert reg.get("tool") is second
    assert len(reg) == 1


async def test_fake_tool_callable():
    """_FakeTool.call 是 async,可被 await。"""
    tool = _FakeTool("test")
    result = await tool.call({"q": "hello"})
    assert "test" in result
    assert "hello" in result
