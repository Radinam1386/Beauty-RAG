"""اتصال به API واقعی سایت — با transport ساختگی، بدون شبکه."""

import json

import httpx
import pytest

from app.integrations.spring_boot.client import SpringBootClient, SpringBootError
from app.listings.service import ListingService, resolve_ad_type
from app.tools.base import ToolRegistry
from app.tools.listing import build_listing_tools

SPACE_AD = {
    "id": "ad-1",
    "adType": "SPACE_RENTAL",
    "title": "اجاره لاین ناخن",
    "description": "لاین ناخن در سالن شیک",
    "cityName": "تهران",
    "neighborhoodName": "ونک",
    "spaceTypeName": "اشتراکی←فضای سالن",
    "speciality": "ناخن←تمام خدمات",
    "monthlyPrice": 3800000.0,
    "dailyPrice": 250000.0,
    "depositPrice": 10000000.0,
    "contactNumber": "09151234567",
}

COURSE_AD = {
    "id": "ad-2",
    "adType": "COURSE",
    "title": "دوره میکاپ",
    "description": "دوره حرفه‌ای میکاپ",
    "cityName": "مشهد",
    "coursePrice": 2500000.0,
    "instructorName": "مریم",
    "slug": "دوره-میکاپ",
}

EQUIPMENT_AD = {
    "id": "ad-3",
    "adType": "EQUIPMENT",
    "title": "صندلی آرایش",
    "description": "صندلی نو",
    "cityName": "شیراز",
    "equipmentCategoryName": "تجهیزات و مبلمان سالن",
    "equipmentContactForPrice": True,
    "slug": "صندلی-آرایش",
}


class MockAPI(httpx.AsyncBaseTransport):
    def __init__(self, payloads: dict | None = None, status: int = 200) -> None:
        self.payloads = payloads or {}
        self.status = status
        self.calls: list[tuple[str, str]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path))
        return httpx.Response(self.status, json=self.payloads.get(request.url.path, {}))


def make_service(transport: httpx.AsyncBaseTransport) -> ListingService:
    client = SpringBootClient(base_url="http://api.test", transport=transport)
    return ListingService(client=client, site_url="https://beautyboss.ir")


async def test_search_maps_live_ad():
    api = MockAPI({"/api/v1/elastic/search-by-filter": {"content": [SPACE_AD], "totalElements": 1}})
    items = await make_service(api).search("ناخن")

    assert api.calls == [("POST", "/api/v1/elastic/search-by-filter")]
    item = items[0]
    assert item["isSample"] is False
    assert item["city"] == "تهران"
    assert item["area"] == "ونک"
    assert "ماهانه" in item["priceLabel"]
    assert "ودیعه" in item["priceLabel"]
    assert item["url"] == "https://beautyboss.ir/ads/space-rental/ad-1"
    # شماره تماس آگهی‌دهنده نباید بیرون برود
    assert "09151234567" not in json.dumps(items, ensure_ascii=False)


async def test_search_filters_by_city():
    api = MockAPI({"/api/v1/elastic/search-by-filter": {"content": [SPACE_AD, COURSE_AD]}})
    items = await make_service(api).search("", city="مشهد")

    assert [i["id"] for i in items] == ["ad-2"]


async def test_search_ranks_relevant_first_and_caps():
    ads = [
        {
            "id": f"ad-{i}",
            "adType": "SPACE_RENTAL",
            "title": f"آگهی شماره {i}",
            "description": "اجاره صندلی",
            "cityName": "تهران",
        }
        for i in range(8)
    ]
    ads[5] = {
        "id": "ad-5",
        "adType": "SPACE_RENTAL",
        "title": "اجاره صندلی رنگ و مش مو",
        "description": "لاین رنگ و مش در سالن",
        "spaceTypeName": "اشتراکی←فضای سالن",
        "cityName": "تهران",
    }
    api = MockAPI({"/api/v1/elastic/search-by-filter": {"content": ads}})
    items = await make_service(api).search("موی مش تهران میخوام", city="تهران")

    assert len(items) <= 6
    assert items[0]["id"] == "ad-5"


async def test_short_token_does_not_match_inside_words():
    irrelevant = {
        "id": "ad-x",
        "adType": "EQUIPMENT",
        "title": "فروش لوازم آرایشگاه",
        "description": "موم و وسایل",
        "cityName": "تهران",
    }
    relevant = {
        "id": "ad-y",
        "adType": "SPACE_RENTAL",
        "title": "اجاره لاین مو",
        "description": "لاین رنگ و مش",
        "cityName": "تهران",
    }
    api = MockAPI({"/api/v1/elastic/search-by-filter": {"content": [irrelevant, relevant]}})
    items = await make_service(api).search("موی مش تهران", city="تهران")

    assert [i["id"] for i in items] == ["ad-y"]


async def test_categories_are_live_ad_types():
    items = await make_service(MockAPI()).categories()

    assert [c["id"] for c in items] == ["SPACE_RENTAL", "COURSE", "EQUIPMENT"]
    assert all(c["name"] for c in items)


async def test_ad_urls_for_course_and_equipment():
    api = MockAPI({"/api/v1/elastic/search-by-filter": {"content": [COURSE_AD, EQUIPMENT_AD]}})
    items = await make_service(api).search("")
    by_id = {item["id"]: item for item in items}

    assert by_id["ad-2"]["url"].startswith("https://beautyboss.ir/courses/ad-2-")
    assert by_id["ad-3"]["url"].startswith("https://beautyboss.ir/equipment/ad-3-")
    assert by_id["ad-3"]["priceLabel"] == "استعلام قیمت"


async def test_details_reads_space_rental_without_phone():
    detail = dict(SPACE_AD, facility="نور مناسب", partnerShipType="FixedـMonthlyـRent")
    api = MockAPI({"/api/v1/spacerentalad/get-one": detail})
    item = await make_service(api).details("ad-1", category="SPACE_RENTAL")

    assert item["rentModel"] == "FixedـMonthlyـRent"
    assert item["facilities"] == "نور مناسب"
    assert "contactNumber" not in item
    assert "09151234567" not in json.dumps(item, ensure_ascii=False)


async def test_api_error_raises():
    with pytest.raises(SpringBootError):
        await make_service(MockAPI(status=500)).search("ناخن")


async def test_tool_reports_api_failure():
    reg = ToolRegistry()
    for tool in build_listing_tools(service=make_service(MockAPI(status=500))):
        reg.register(tool)

    result = await reg.dispatch("search_listings", {"query": "ناخن"})

    assert result.is_error
    assert "آگهی" in result.content


def test_resolve_ad_type_from_persian():
    assert resolve_ad_type("دوره میکاپ") == "COURSE"
    assert resolve_ad_type("خرید تجهیزات") == "EQUIPMENT"
    assert resolve_ad_type("اجاره لاین") == "SPACE_RENTAL"
    assert resolve_ad_type(None) is None
