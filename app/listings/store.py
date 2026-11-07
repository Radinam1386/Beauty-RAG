"""انبار آگهی نمونه — تا اتصال Spring Boot (فاز بعدی استقرار سایت).

این دادهها با SAMPLE_LISTINGS فرانت همراستا هستند تا UI و چت یک چیز را نشان دهند.
جستجو ساده و فارسی‌پسند است؛ pgvector و RAG کار فاز ۴ است.
"""

from __future__ import annotations

import re
from typing import Any

ZWNJ = "\u200c"

CATEGORIES = [
    {"id": "hair", "name": "کوتاهی و رنگ مو"},
    {"id": "makeup", "name": "میکاپ و گریم"},
    {"id": "nail", "name": "ناخن"},
    {"id": "skin", "name": "پوست و لیفت"},
    {"id": "lash", "name": "مژه و ابرو"},
]

LISTINGS: list[dict[str, Any]] = [
    {
        "id": "sample-1",
        "title": "رنگ و مش مو با مواد ارگانیک",
        "categoryId": "hair",
        "categoryName": "کوتاهی و رنگ مو",
        "city": "تهران",
        "area": "سعادت آباد",
        "priceLabel": "از ۹۵۰٬۰۰۰ تومان",
        "providerName": "سالن آرتمیس",
        "url": "https://beautyboss.ir/listings/sample-1",
        "isSample": True,
    },
    {
        "id": "sample-2",
        "title": "میکاپ عروس حرفه‌ای به‌همراه تست میکاپ",
        "categoryId": "makeup",
        "categoryName": "میکاپ و گریم",
        "city": "تهران",
        "area": "ولنجک",
        "priceLabel": "توافقی",
        "providerName": "آتلیه نیکا",
        "url": "https://beautyboss.ir/listings/sample-2",
        "isSample": True,
    },
    {
        "id": "sample-3",
        "title": "کاشت ناخن پودر و ژلیش",
        "categoryId": "nail",
        "categoryName": "ناخن",
        "city": "کرج",
        "area": "عظیمیه",
        "priceLabel": "از ۴۸۰٬۰۰۰ تومان",
        "providerName": "استودیو رها",
        "url": "https://beautyboss.ir/listings/sample-3",
        "isSample": True,
    },
    {
        "id": "sample-4",
        "title": "لیفت و پاکسازی پوست با دستگاه",
        "categoryId": "skin",
        "categoryName": "پوست و لیفت",
        "city": "تهران",
        "area": "جردن",
        "priceLabel": "از ۱٬۲۰۰٬۰۰۰ تومان",
        "providerName": "کلینیک روژان",
        "url": "https://beautyboss.ir/listings/sample-4",
        "isSample": True,
    },
    {
        "id": "sample-5",
        "title": "کاشت مژه و لیفت مژه",
        "categoryId": "lash",
        "categoryName": "مژه و ابرو",
        "city": "تهران",
        "area": "میرداماد",
        "priceLabel": "از ۷۵۰٬۰۰۰ تومان",
        "providerName": "استودیو ماهور",
        "url": "https://beautyboss.ir/listings/sample-5",
        "isSample": True,
    },
    {
        "id": "sample-6",
        "title": "رنگ و مش مو در ونک",
        "categoryId": "hair",
        "categoryName": "کوتاهی و رنگ مو",
        "city": "تهران",
        "area": "ونک",
        "priceLabel": "از ۱٬۱۰۰٬۰۰۰ تومان",
        "providerName": "سالن ونک",
        "url": "https://beautyboss.ir/listings/sample-6",
        "isSample": True,
    },
]


def normalize(s: str) -> str:
    s = (s or "").replace(ZWNJ, " ").replace("ي", "ی").replace("ك", "ک")
    s = s.replace("آ", "ا").replace("أ", "ا").replace("إ", "ا")
    s = re.sub(r"[\u064B-\u0652]", "", s)  # اعراب
    return s.lower().strip()


def get_categories() -> list[dict[str, Any]]:
    return [dict(c) for c in CATEGORIES]


def get_listing(listing_id: str) -> dict[str, Any] | None:
    for item in LISTINGS:
        if item["id"] == listing_id:
            return dict(item)
    return None


def search_listings(
    query: str = "",
    category: str | None = None,
    city: str | None = None,
) -> list[dict[str, Any]]:
    q = normalize(query)
    tokens = [t for t in re.split(r"[\s،,]+", q) if len(t) > 1]
    cat = normalize(category) if category else None
    city_n = normalize(city) if city else None

    results: list[dict[str, Any]] = []
    for item in LISTINGS:
        hay = normalize(
            " ".join(
                [
                    item["title"],
                    item["city"],
                    item.get("area") or "",
                    item["categoryName"],
                    item["categoryId"],
                    item.get("providerName") or "",
                ]
            )
        )
        if cat and cat not in normalize(item["categoryId"]) and cat not in normalize(item["categoryName"]):
            continue
        if city_n and city_n not in normalize(item["city"]) and city_n not in normalize(item.get("area") or ""):
            continue
        if tokens and not any(t in hay for t in tokens):
            continue
        results.append(dict(item))
    return results
