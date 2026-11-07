from app.knowledge.store import search_knowledge, get_article
from app.tools.knowledge import build_knowledge_tools
from app.tools.base import ToolRegistry


def test_search_sunscreen():
    items = search_knowledge("ضدآفتاب")
    assert items
    assert any(i["id"] == "sunscreen" for i in items)


def test_search_dry_skin():
    items = search_knowledge("پوست خشک مرطوبکننده")
    assert items
    assert any(i["id"] == "moisturizer-dry" for i in items)


def test_get_article():
    a = get_article("skin-routine")
    assert a and "پوست" in a["title"] or a["id"] == "skin-routine"


def test_tool_search():
    reg = ToolRegistry()
    for t in build_knowledge_tools():
        reg.register(t)
    import asyncio
    result = asyncio.run(reg.dispatch("search_knowledge", {"query": "ضدآفتاب"}))
    assert not result.is_error
    assert "ضدآفتاب" in result.content
