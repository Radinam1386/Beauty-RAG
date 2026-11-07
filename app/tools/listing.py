"""ابزارهای آگهی — فاز ۳.

جستجو و جزئیات از API واقعی سایت (ListingService) می‌آید؛ بدون کلاینت، انبار نمونه.
ثبت درخواست فقط برای کاربر لاگین‌شده و در دیتابیس خودمان ذخیره می‌شود.
"""

from __future__ import annotations

import json
from typing import Any

from app.auth.identity import Identity
from app.integrations.spring_boot.client import SpringBootError
from app.listings.service import ListingService
from app.tools.base import Tool, ToolResult

NO_API = (
    "ارتباط با سایت BeautyBoss برقرار نشد؛ الان نمی‌توانم آگهی واقعی نشان دهم. "
    "از خودت آگهی، قیمت یا لینک نساز."
)


def _listings_payload(items: list[dict[str, Any]]) -> str:
    return json.dumps(items, ensure_ascii=False)


def build_listing_tools(
    identity: Identity | None = None,
    service: ListingService | None = None,
) -> list[Tool]:
    svc = service or ListingService()

    async def search_handler(args: dict[str, Any]) -> ToolResult:
        try:
            items = await svc.search(
                args.get("query") or "",
                category=args.get("category"),
                city=args.get("city"),
            )
        except SpringBootError:
            return ToolResult(content=NO_API, is_error=True)
        if not items:
            return ToolResult(
                content="هیچ آگهی مطابقی پیدا نشد. پیشنهاد کن فیلترها (نوع آگهی، شهر، کلیدواژه) را ساده‌تر کنند.",
                meta={"listings": []},
            )
        return ToolResult(
            content=_listings_payload(items),
            meta={"listings": items},
        )

    async def details_handler(args: dict[str, Any]) -> ToolResult:
        try:
            item = await svc.details(
                args.get("listing_id") or "",
                category=args.get("category"),
            )
        except SpringBootError:
            return ToolResult(content=NO_API, is_error=True)
        if not item:
            return ToolResult(
                content="جزئیات این آگهی پیدا نشد. از نتایج جستجو استفاده کن یا لینک آگهی را بده.",
                is_error=True,
            )
        return ToolResult(content=_listings_payload([item]), meta={"listings": [item]})

    async def categories_handler(args: dict[str, Any]) -> ToolResult:
        try:
            categories = await svc.categories()
        except SpringBootError:
            return ToolResult(content=NO_API, is_error=True)
        return ToolResult(content=json.dumps(categories, ensure_ascii=False))

    async def submit_handler(args: dict[str, Any]) -> ToolResult:
        if identity is None or identity.is_guest:
            return ToolResult(
                content="برای ثبت درخواست آگهی باید وارد حساب کاربری شوید. ثبت فقط برای کاربر لاگین‌شده است.",
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
        # ذخیره در ChatService انجام می‌شود اگر identity کاربر باشد؛ اینجا فقط تأیید می‌دهد.
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
                "جستجوی آگهی‌های واقعی سایت BeautyBoss: اجاره فضا (لاین، صندلی، تخت، اتاق، سالن)، "
                "دوره آموزشی و خرید تجهیزات. نتیجه معمولاً چند آگهی برتر است و در رابط کاربری "
                "به‌صورت کارت نشان داده می‌شود؛ عنوان، شهر و قیمت را فقط از همین نتیجه بگو و "
                "از خودت آگهی یا قیمت نساز."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "متن جستجو مثل: اجاره لاین ناخن، دوره میکاپ، صندلی آرایش",
                    },
                    "category": {
                        "type": "string",
                        "description": (
                            "نوع آگهی: SPACE_RENTAL (اجاره فضا) یا COURSE (دوره) یا "
                            "EQUIPMENT (خرید تجهیزات). اگر کاربر نوع را نگفته، خالی بگذار."
                        ),
                    },
                    "city": {
                        "type": "string",
                        "description": "نام شهر مثل تهران، مشهد، اصفهان",
                    },
                },
                "required": ["query"],
            },
            handler=search_handler,
        ),
        Tool(
            name="get_listing_details",
            description=(
                "جزئیات کامل یک آگهی سایت با شناسه آن: توضیحات، مدل اجاره، امکانات و قیمت‌های همان آگهی. "
                "شماره تماس آگهی‌دهنده را برنگردان."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "listing_id": {"type": "string", "description": "شناسه آگهی از نتیجه جستجو"},
                    "category": {
                        "type": "string",
                        "description": "نوع آگهی خروجی جستجو: SPACE_RENTAL یا COURSE یا EQUIPMENT",
                    },
                },
                "required": ["listing_id"],
            },
            handler=details_handler,
        ),
        Tool(
            name="get_listing_categories",
            description="فهرست نوع آگهی‌های سایت BeautyBoss (اجاره فضا، دوره آموزشی، خرید تجهیزات).",
            parameters={"type": "object", "properties": {}},
            handler=categories_handler,
        ),
        Tool(
            name="prepare_listing_request",
            description=(
                "ثبت درخواست آگهی. فیلدها را مرحله‌به‌مرحله جمع کن. ثبت نهایی فقط بعد از تأیید صریح کاربر لاگین‌شده."
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
