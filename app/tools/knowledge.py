"""ابزار دانش مراقبت زیبایی — فاز ۴.

جستجو در مقالات راهنمای داخلی. پاسخ نهایی باید منبع داشته باشد.
جایگزین توصیه پزشکی شخصی نیست.
"""

from __future__ import annotations

import json
from typing import Any

from app.knowledge.store import get_article, search_knowledge
from app.tools.base import Tool, ToolResult


async def search_handler(args: dict[str, Any]) -> ToolResult:
    query = (args.get("query") or "").strip()
    if not query:
        return ToolResult(content="عبارت جستجو خالی است.", is_error=True)
    items = search_knowledge(query)
    if not items:
        return ToolResult(
            content="در راهنمای داخلی مطلبی برای این موضوع پیدا نشد. از دانش عمومی با احتیاط کمک کن و بگو منبع داخلی نداری.",
            meta={"sources": []},
        )
    # بدنه کامل را به مدل بده تا خلاصه کند؛ منبع را نگه دار
    payload = [
        {
            "id": it["id"],
            "title": it["title"],
            "content": it["content"],
            "source": it["source"],
            "url": it["url"],
        }
        for it in items[:4]
    ]
    return ToolResult(
        content=json.dumps(payload, ensure_ascii=False),
        meta={"sources": [{"title": it["source"], "url": it["url"]} for it in payload]},
    )


async def article_handler(args: dict[str, Any]) -> ToolResult:
    item = get_article(args.get("article_id") or "")
    if not item:
        return ToolResult(content="مقاله پیدا نشد.", is_error=True)
    return ToolResult(
        content=json.dumps(item, ensure_ascii=False),
        meta={"sources": [{"title": item["source"], "url": item["url"]}]},
    )


def build_knowledge_tools() -> list[Tool]:
    return [
        Tool(
            name="search_knowledge",
            description=(
                "جستجو در راهنمای مراقبت پوست، مو، ناخن و آرایش BeautyBoss. "
                "پاسخ را بر اساس نتیجه این ابزار بده و منبع را ذکر کن. "
                "برای تشخیص یا درمان پزشکی شخصی، ارجاع به متخصص بده."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "موضوع مثل: پوست خشک، ضدآفتاب، ریزش مو"},
                },
                "required": ["query"],
            },
            handler=search_handler,
        ),
        Tool(
            name="get_knowledge_article",
            description="دریافت متن کامل یک مقاله راهنما با شناسه آن.",
            parameters={
                "type": "object",
                "properties": {
                    "article_id": {"type": "string", "description": "شناسه مقاله"},
                },
                "required": ["article_id"],
            },
            handler=article_handler,
        ),
    ]
