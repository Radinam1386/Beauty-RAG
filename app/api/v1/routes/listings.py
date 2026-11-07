import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import IdentityDep, get_spring_boot_client
from app.api.v1.schemas.listings import (
    ListingCategoryOut,
    ListingOut,
    ListingRequestIn,
    ListingRequestOut,
    ListingSearchIn,
)
from app.auth.identity import Identity
from app.chat.repository import ChatRepository
from app.database.models import ListingRequest
from app.database.session import get_session
from app.integrations.spring_boot.client import SpringBootClient, SpringBootError
from app.listings.service import ListingService
from typing import Annotated

router = APIRouter(tags=["Listings"])

SITE_UNAVAILABLE = "ارتباط با سایت BeautyBoss برقرار نشد"


def get_listing_service(
    client: Annotated[SpringBootClient, Depends(get_spring_boot_client)],
) -> ListingService:
    return ListingService(client=client)


ListingSvc = Annotated[ListingService, Depends(get_listing_service)]


@router.get("/listings/categories", response_model=list[ListingCategoryOut])
async def categories(svc: ListingSvc):
    try:
        return await svc.categories()
    except SpringBootError as exc:
        raise HTTPException(status_code=502, detail=SITE_UNAVAILABLE) from exc


@router.post("/listings/search", response_model=list[ListingOut])
async def search(payload: ListingSearchIn, svc: ListingSvc):
    try:
        items = await svc.search(payload.query, category=payload.categoryId, city=payload.city)
    except SpringBootError as exc:
        raise HTTPException(status_code=502, detail=SITE_UNAVAILABLE) from exc
    return [ListingOut(**item) for item in items]


@router.get("/listings/{listing_id}", response_model=ListingOut)
async def details(listing_id: str, svc: ListingSvc, category: str | None = Query(default=None)):
    try:
        item = await svc.details(listing_id, category=category)
    except SpringBootError as exc:
        raise HTTPException(status_code=502, detail=SITE_UNAVAILABLE) from exc
    if not item:
        raise HTTPException(status_code=404, detail="آگهی پیدا نشد")
    return ListingOut(**item)


@router.post("/listing-requests", response_model=ListingRequestOut, status_code=201)
async def submit_request(
    payload: ListingRequestIn,
    identity: IdentityDep,
    session: AsyncSession = Depends(get_session),
):
    """ثبت درخواست آگهی فقط برای کاربر لاگین‌شده — مطابق سند فاز ۳."""
    if identity.is_guest:
        raise HTTPException(
            status_code=401,
            detail="برای ثبت درخواست آگهی باید وارد حساب کاربری شوید",
        )
    repo = ChatRepository(session)
    phone = payload.contactPhone.strip()
    if not phone.startswith("09") or not phone.isdigit() or len(phone) != 11:
        raise HTTPException(status_code=422, detail="شماره تماس باید موبایل ایران باشد (09xxxxxxxxx)")

    request_id = uuid.uuid4()
    session.add(
        ListingRequest(
            id=str(request_id),
            conversation_id=payload.conversationId,
            external_user_id=identity.external_user_id or "",
            category_id=payload.categoryId,
            title=payload.title,
            description=payload.description,
            city=payload.city,
            area=payload.area,
            budget_label=payload.budgetLabel,
            contact_phone=phone,
            status="review",
        )
    )
    await session.commit()
    return ListingRequestOut(
        id=str(request_id),
        status="review",
        message="درخواست آگهی شما ثبت شد و در صف بررسی است. نتیجه از طریق حساب کاربری اطلاع داده می‌شود.",
    )
