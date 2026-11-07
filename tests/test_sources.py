from app.knowledge.sources import get_source, load_chunks, search_sources
from app.knowledge.store import get_article, search_knowledge, KNOWLEDGE


def test_sources_are_loaded():
    chunks = load_chunks()
    assert len(chunks) > 40
    assert any(c.url.startswith("http") for c in chunks)
    assert any(c.language == "fa" for c in chunks)


def test_persian_query_finds_english_source():
    items = search_sources("ضدآفتاب")
    assert items
    assert any("sun" in item["title"].lower() or "sunscreen" in item["title"].lower() for item in items)


def test_hair_loss_query_finds_hair_sources():
    items = search_sources("ریزش مو")
    assert items
    assert any("hair" in item["title"].lower() for item in items)


def test_ingredient_query_finds_talc():
    items = search_sources("تالک")
    assert items
    assert any("talc" in item["title"].lower() for item in items)


def test_persian_source_is_searchable():
    items = search_sources("اصالت کالا")
    assert items
    assert any(item["url"] for item in items)


def test_search_knowledge_merges_sources():
    ids = [item["id"] for item in search_knowledge("ضدآفتاب")]
    # هم مقاله دستی فارسی، هم منبع رسمی FDA
    assert any(i in ids for i in [k["id"] for k in KNOWLEDGE])
    assert any(i.startswith("fda-sunscreen-guide") for i in ids)


def test_source_results_are_not_duplicated():
    titles = [item["title"] for item in search_sources("ریزش مو")]
    assert len(titles) == len(set(titles))


def test_get_article_returns_source_chunk():
    chunk = load_chunks()[0]
    item = get_article(chunk.id)
    assert item and item["id"] == chunk.id
    assert item["url"] == chunk.url
    assert len(item["content"]) >= len(chunk.content)


def test_source_results_are_trimmed():
    items = search_sources("پوست")
    assert items
    assert all(len(item["content"]) <= 1200 for item in items)
