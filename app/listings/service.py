from __future__ import annotations

from app.listings.store import get_categories, get_listing, search_listings


class ListingService:
    async def categories(self) -> list[dict]:
        return get_categories()

    async def search(self, query: str, category: str | None = None, city: str | None = None) -> list[dict]:
        return search_listings(query or "", category=category, city=city)

    async def details(self, listing_id: str) -> dict | None:
        return get_listing(listing_id)
