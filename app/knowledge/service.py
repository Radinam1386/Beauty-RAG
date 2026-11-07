from __future__ import annotations

from app.knowledge.store import get_article, search_knowledge


class KnowledgeService:
    async def search(self, query: str) -> list[dict]:
        return search_knowledge(query or "")

    async def article(self, article_id: str) -> dict | None:
        return get_article(article_id)
