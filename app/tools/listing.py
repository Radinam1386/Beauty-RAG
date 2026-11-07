"""ابزارهای آگهی — فاز ۳.

جستجو و جزئیات با انبار نمونه کار میکند (بدون Spring).
ثبت درخواست فقط برای کاربر لاگینشده و در دیتابیس ذخیره میشود.
"""

from __future__ import annotations

import json
from typing import Any

from app.auth.identity import Identity
from app.listings.store import get_listing, search_listings
from app.tools.base import Tool, ToolResult


def _listings_payload(items: list[dict[str, Any]]) -> str:
    return json.dumps(items, ensure_ascii=False)


def build_listing_tools(identity: Identity | None = None) -> list[Tool]:
    async def search_handler(args: dict[str, Any]) -> ToolResult:
        items = search_listings(
            args.get("query") or "",
            category=args.get("category"),
            city=args.get("city"),
        )
        if not items:
            return ToolResult(
                content="هیچ آگهی مطابقی پیدا نشد. پیشنهاد کن فیلترها (دسته، شهر، محله) را تغییر بدهند.",
                meta={"listings": []},
            )
        return ToolResult(
            content=_listings_payload(items),
            meta={"listings": items},
        )

    async def details_handler(args: dict[str, Any]) -> ToolResult:
        item = get_listing(args.get("listing_id") or "")
        if not item:
            return ToolResult(content="آگهی پیدا نشد.", is_error=True)
        return ToolResult(content=_listings_payload([item]), meta={"listings": [item]})

    async def categories_handler(args: dict[str, Any]) -> ToolResult:
        from app.listings.store import CATEGORIES
        return ToolResult(content=json.dumps(CATEGORIES, ensure_ascii=False))

    async def submit_handler(args: dict[str, Any]) -> ToolResult:
        if identity is None or identity.is_guest:
            return ToolResult(
                content="برای ثبت درخواست آگهی باید وارد حساب کاربری شوید. ثبت فقط برای کاربر لاگینشده است.",
                is_error=True,
            )
        required = ["categoryId", "title", "description", "city", "contactPhone"]
        missing = [k for k in required if not (args.get(k) or "").strip()]
        if missing:
            return ToolResult(
                content=json.dumps(
                    {"status": "draft", "missing": missing, "message": "این فیلدها هنوز کامل نیست: " + "، ".join(missing)},
                    ensure_ascii=False,
                ),
                is_error=False,
            )
        phone = str(args.get("contactPhone") or "").strip()
        if not (phone.startswith("09") and phone.isdigit() and len(phone) == 11):
            return ToolResult(
                content="شماره تماس باید موبایل ایران باشد (09xxxxxxxxx).",
                is_error=True,
            )
        # ذخیره در ChatService انجام میشود اگر identity کاربر باشد؛ اینجا فقط تأیید میدهد.
        return ToolResult(
            content=json.dumps(
                {
                    "status": "ready_to_submit",
                    "draft": {k: args.get(k) for k in args},
                    "message": "همه فیلدها کامل است. فقط با تأیید صریح کاربر submit کن.",
                },
                ensure_ascii=False,
            )
        )

    return [
        Tool(
            name="search_listings",
            description=(
                "جستجوی آگهیهای سایت BeautyBoss. فقط نتیجه این ابزار را به کاربر نشان بده "
                "و قیمت/لینک را از خودت نساز."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "متن جستجو مثل: رنگ مو تهران"},
                    "category": {"type": "string", "description": "شناسه دسته: hair, makeup, nail, skin, lash"},
                    "city": {"type": "string", "description": "شهر مثل تهران"},
                },
                "required": ["query"],
            },
            handler=search_handler,
        ),
        Tool(
            name="get_listing_details",
            description="دریافت جزئیات کامل یک آگهی با شناسه آن.",
            parameters={
                "type": "object",
                "properties": {
                    "listing_id": {"type": "string", "description": "شناسه آگهی"},
                },
                "required": ["listing_id"],
            },
            handler=details_handler,
        ),
        Tool(
            name="get_listing_categories",
            description="فهرست دستهبندیهای آگهی سایت.",
            parameters={"type": "object", "properties": {}},
            handler=categories_handler,
        ),
        Tool(
            name="prepare_listing_request",
            description=(
                "ثبت درخواست آگهی. فیلدها را مرحلهاجمع کن. ثبت نهایی فقط بعد از تأیید صریح کاربر لاگینشده."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "categoryId": {"type": "string", "description": "شناسه دسته"},
                    "title": {"type": "string", "description": "عنوان درخواست"},
                    "description": {"type": "string", "description": "توضیحات"},
                    "city": {"type": "string", "description": "شهر"},
                    "area": {"type": "string", "description": "محله"},
                    "budgetLabel": {"type": "string", "description": "بودجه"},
                    "contactPhone": {"type": "string", "description": "شماره تماس 09xxxxxxxxx"},
                },
                "required": ["categoryId", "title", "description", "city", "contactPhone"],
            },
            handler=submit_handler,
        ),
    ]
