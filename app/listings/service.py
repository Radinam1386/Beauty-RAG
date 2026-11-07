"""سرویس آگهی: داده زنده سایت یا انبار نمونه.

اگر کلاینت سایت (SpringBootClient) داده شود، همه‌چیز از API واقعی beautyboss.ir می‌آید.
بدون کلاینت، برای تست و توسعه آفلاین، همان انبار نمونه قبلی استفاده می‌شود.
اطلاعات خصوصی آگهی‌دهنده (شماره تماس، آدرس دقیق، شناسه کاربر) هرگز به خروجی نمی‌رود.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from app.core.config import get_settings
from app.integrations.spring_boot.client import SpringBootClient
from app.listings.store import get_categories, get_listing, search_listings

AD_TYPES = {
    "SPACE_RENTAL": "اجاره فضا",
    "COURSE": "دوره آموزشی",
    "EQUIPMENT": "خرید تجهیزات",
}

# مسیرهای صفحه آگهی روی سایت (از خود سایت تأیید شده)
AD_URL_PATHS = {
    "SPACE_RENTAL": "/ads/space-rental/{id}",
    "COURSE": "/courses/{id}-{slug}",
    "EQUIPMENT": "/equipment/{id}-{slug}",
}

SITE_LIST = "/ads-list"

# چند نتیجه بیشتر از سایت می‌گیریم، خودمان رتبه می‌دهیم و فقط بهترین‌ها را نشان می‌دهیم.
FETCH_SIZE = 100
SEARCH_LIMIT = 6

# برای اینکه اصطلاح‌های رایج کاربر و آگهی به هم برسند (مش = رنگ و لایت/بالیاژ)
SYNONYMS = {
    "مش": ["رنگ", "لایت", "بالیاژ", "هایلایت"],
    "مو": ["موی"],
    "ناخن": ["مانیکور", "پدیکور", "کاشت"],
    "مژه": ["اکستنشن", "لیفت"],
    "ابرو": ["میکروبلیدینگ", "فیبروز"],
    "میکاپ": ["گریم", "عروس"],
    "پوست": ["فیشیال", "پاکسازی"],
    "کوتاهی": ["کوتاه", "استایل"],
}

STOPWORDS = {
    "میخوام", "می‌خوام", "میخواهم", "می‌خواهم", "میخواستم", "توی", "تو", "در", "داخل",
    "برای", "از", "با", "و", "یا", "یه", "یک", "دنبال", "هستم", "میگردم", "می‌گردم",
    "بگرد", "پیدا", "کن", "کنم", "آگهی", "آگهی‌ها", "آگهیها", "نیاز", "دارم", "چه",
    "کدام", "چند", "تا", "هم", "رو", "را", "که", "من", "موجود", "هست", "لطفا", "لطفاً",
    "دوره", "دوره‌های", "دورههای", "آموزش",
}


def _normalize(text: str) -> str:
    value = (text or "").replace("\u200c", " ").replace("ي", "ی").replace("ك", "ک")
    value = value.replace("آ", "ا").replace("أ", "ا").replace("إ", "ا")
    value = re.sub(r"[\u064B-\u0652]", "", value)
    return re.sub(r"\s+", " ", value).lower().strip()


def _query_tokens(query: str, city: str | None = None) -> list[str]:
    """کلمه‌های معنی‌دار جستجو؛ بدون کلمه‌های پرسشی و بدون نام شهر."""
    city_n = _normalize(city or "")
    tokens: list[str] = []
    for word in _normalize(query).split():
        if len(word) < 2 or word in STOPWORDS:
            continue
        if city_n and word in city_n:
            continue
        tokens.append(word)
        if len(word) >= 3 and word.endswith("ی"):
            tokens.append(word[:-1])
    return list(dict.fromkeys(tokens))


def _expand(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        expanded.extend(SYNONYMS.get(token, []))
    return list(dict.fromkeys(expanded))


def _hits(text: str, tokens: list[str]) -> int:
    """تعداد کلمه‌های جستجو که در متن پیدا می‌شوند (تطابق کلمه‌ای، نه زیررشته)."""
    words = re.findall(r"[0-9a-z\u0600-\u06FF]+", _normalize(text))
    count = 0
    for token in tokens:
        if token in words or (len(token) >= 4 and any(w.startswith(token) for w in words)):
            count += 1
    return count


def _relevance(item: dict[str, Any], tokens: list[str]) -> int:
    """امتیاز تطابق برای مرتب‌کردن نتایج سایت: عنوان > تخصص > بقیه متن."""
    title = item.get("title") or ""
    meta = " ".join(
        [item.get("categoryName") or "", item.get("speciality") or ""]
    )
    body = " ".join(
        [item.get("description") or "", item.get("city") or "", item.get("area") or ""]
    )
    return 3 * _hits(title, tokens) + 2 * _hits(meta, tokens) + _hits(body, tokens)


def resolve_ad_type(value: str | None) -> str | None:
    """نوع آگهی را از کد انگلیسی یا توضیح فارسی کاربر پیدا می‌کند."""
    if not value:
        return None
    text = value.strip()
    upper = text.upper()
    if upper in AD_TYPES:
        return upper
    if any(word in text for word in ("دوره", "آموزش")):
        return "COURSE"
    if any(word in text for word in ("تجهیز", "خرید", "لوازم", "دستگاه")):
        return "EQUIPMENT"
    if any(word in text for word in ("اجاره", "فضا", "سالن", "اتاق", "لاین", "صندلی", "تخت")):
        return "SPACE_RENTAL"
    return None


def _toman(value: Any) -> str | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return f"{int(round(number)):,}".replace(",", "٬") + " تومان"


def _price_label(item: dict[str, Any], ad_type: str) -> str:
    if ad_type == "COURSE":
        return _toman(item.get("coursePrice")) or "توافقی"
    if ad_type == "EQUIPMENT":
        if item.get("equipmentContactForPrice") or item.get("contactForPrice"):
            return "استعلام قیمت"
        return _toman(item.get("equipmentPrice")) or "توافقی"

    parts = []
    daily = _toman(item.get("dailyPrice"))
    monthly = _toman(item.get("monthlyPrice"))
    deposit = _toman(item.get("depositPrice"))
    if daily:
        parts.append(f"روزانه {daily}")
    if monthly:
        parts.append(f"ماهانه {monthly}")
    if deposit:
        parts.append(f"ودیعه {deposit}")
    return " · ".join(parts) if parts else "توافقی"


def _category_name(item: dict[str, Any], ad_type: str) -> str:
    if ad_type == "COURSE":
        return "دوره آموزشی"
    if ad_type == "EQUIPMENT":
        return item.get("equipmentCategoryName") or item.get("categoryTitle") or "خرید تجهیزات"
    return item.get("spaceTypeName") or item.get("speciality") or "اجاره فضا"


def _ad_url(item: dict[str, Any], site_url: str, ad_type: str) -> str:
    path = AD_URL_PATHS.get(ad_type)
    ad_id = item.get("id")
    if not path or not ad_id:
        return f"{site_url}{SITE_LIST}"
    if "{slug}" in path:
        slug = (item.get("slug") or "").strip()
        if not slug:
            return f"{site_url}{SITE_LIST}"
        return site_url + path.format(id=ad_id, slug=quote(slug, safe=""))
    return site_url + path.format(id=ad_id)


def normalize_listing(item: dict[str, Any], site_url: str) -> dict[str, Any]:
    """آگهی API را به شکل مشترک ListingSummary تبدیل می‌کند."""
    ad_type = item.get("adType") or ""
    return {
        "id": str(item.get("id") or ""),
        "title": item.get("title") or "",
        "categoryId": ad_type,
        "categoryName": _category_name(item, ad_type),
        "speciality": item.get("speciality") or None,
        "city": item.get("cityName") or "",
        "area": item.get("neighborhoodName") or None,
        "priceLabel": _price_label(item, ad_type),
        "providerName": item.get("instructorName") or None,
        "url": _ad_url(item, site_url, ad_type),
        "isSample": False,
        "description": (item.get("description") or "").strip(),
    }


class ListingService:
    def __init__(
        self,
        client: SpringBootClient | None = None,
        site_url: str | None = None,
    ) -> None:
        settings = get_settings()
        self.client = client
        self.site_url = (site_url or settings.beautyboss_site_url).rstrip("/")

    async def categories(self) -> list[dict]:
        if self.client is None:
            return get_categories()
        return [{"id": key, "name": name} for key, name in AD_TYPES.items()]

    async def search(
        self,
        query: str = "",
        category: str | None = None,
        city: str | None = None,
    ) -> list[dict]:
        if self.client is None:
            return search_listings(query or "", category=category, city=city)

        tokens = _expand(_query_tokens(query or "", city))
        data = await self.client.search_ads(
            keyword=" ".join(tokens) or (query or ""),
            ad_type=resolve_ad_type(category),
            size=FETCH_SIZE,
        )
        items = [
            normalize_listing(item, self.site_url)
            for item in data.get("content") or []
            if item.get("id")
        ]
        if city:
            needle = _normalize(city)
            items = [
                item
                for item in items
                if needle in _normalize(f"{item['city']} {item['area'] or ''}")
            ]
        if tokens:
            scored = [(_relevance(item, tokens), item) for item in items]
            relevant = [pair for pair in scored if pair[0] > 0]
            if relevant:
                relevant.sort(key=lambda pair: pair[0], reverse=True)
                items = [item for _, item in relevant]
        return items[:SEARCH_LIMIT]

    async def details(self, listing_id: str, category: str | None = None) -> dict | None:
        if self.client is None:
            return get_listing(listing_id)

        ad_type = resolve_ad_type(category)
        candidates = [ad_type] if ad_type else ["SPACE_RENTAL", "EQUIPMENT"]
        for kind in candidates:
            data = await self.client.get_ad(listing_id, kind)
            if not data:
                continue
            merged = dict(data)
            merged.setdefault("adType", kind)
            item = normalize_listing(merged, self.site_url)
            item["rentModel"] = data.get("partnerShipType")
            item["facilities"] = data.get("facility")
            return item
        return None
