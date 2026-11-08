import logging

from app.ai.prompts.system import KNOWLEDGE_END, KNOWLEDGE_START, build_system_prompt
from app.knowledge.loader import load_knowledge
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


# --- مرحله A: دانش ثابت از پوشه knowledge/ ---


def test_load_knowledge_reads_markdown_files():
    text = load_knowledge()
    assert text.strip()
    assert "راهنمای سایت BeautyBoss" in text
    assert "راهنمای استفاده از محصولات" in text
    assert len(text) > 1000


def test_load_knowledge_missing_dir_returns_empty(tmp_path):
    assert load_knowledge(tmp_path / "nope") == ""


def test_load_knowledge_empty_dir_returns_empty(tmp_path):
    assert load_knowledge(tmp_path) == ""


def test_load_knowledge_warns_when_large(tmp_path, caplog):
    (tmp_path / "big.md").write_text("## بخش\n" + "x" * 20_001, encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        text = load_knowledge(tmp_path)
    assert len(text) > 20_000
    assert "RAG" in caplog.text


def test_system_prompt_does_not_include_site_knowledge():
    prompt = build_system_prompt()
    assert KNOWLEDGE_START not in prompt
    assert KNOWLEDGE_END not in prompt


def test_system_prompt_without_knowledge_has_no_block():
    prompt = build_system_prompt(knowledge="")
    assert KNOWLEDGE_START not in prompt
    assert KNOWLEDGE_END not in prompt
