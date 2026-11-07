import pytest

from app.tools.base import Tool, ToolRegistry, ToolResult
from app.tools.listing import build_listing_tools


async def echo_handler(args):
    return ToolResult(content=f"echo:{args.get('text', '')}")


def test_register_and_schema():
    tool = Tool(
        name="echo",
        description="تست",
        parameters={"type": "object", "properties": {}},
        handler=echo_handler,
    )
    reg = ToolRegistry()
    reg.register(tool)
    assert reg.names() == ["echo"]
    schema = reg.to_openai_schemas()[0]
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "echo"


def test_duplicate_register_raises():
    tool = Tool(
        name="echo",
        description="تست",
        parameters={"type": "object", "properties": {}},
        handler=echo_handler,
    )
    reg = ToolRegistry()
    reg.register(tool)
    with pytest.raises(ValueError):
        reg.register(tool)


async def test_dispatch_missing_is_error():
    reg = ToolRegistry()
    result = await reg.dispatch("nope", {})
    assert result.is_error


async def test_dispatch_runs_handler():
    tool = Tool(
        name="echo",
        description="تست",
        parameters={"type": "object", "properties": {}},
        handler=echo_handler,
    )
    reg = ToolRegistry()
    reg.register(tool)
    result = await reg.dispatch("echo", {"text": "سلام"})
    assert result.content == "echo:سلام"
    assert not result.is_error


def test_listing_tools_exist():
    names = [t.name for t in build_listing_tools()]
    assert "search_listings" in names
    assert "get_listing_details" in names
    assert "get_listing_categories" in names


async def test_listing_tools_search_works():
    reg = ToolRegistry()
    for t in build_listing_tools():
        reg.register(t)
    result = await reg.dispatch("search_listings", {"query": "رنگ مو"})
    assert not result.is_error
    assert "sample-1" in result.content
    assert result.meta["listings"]
