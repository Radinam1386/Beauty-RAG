import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import IdentityDep
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
from app.listings.service import ListingService
from typing import Annotated

router = APIRouter(tags=["Listings"])


def get_listing_service() -> ListingService:
    return ListingService()


ListingSvc = Annotated[ListingService, Depends(get_listing_service)]


@router.get("/listings/categories", response_model=list[ListingCategoryOut])
async def categories(svc: ListingSvc):
    return await svc.categories()


@router.post("/listings/search", response_model=list[ListingOut])
async def search(payload: ListingSearchIn, svc: ListingSvc):
    items = await svc.search(payload.query, category=payload.categoryId, city=payload.city)
    return [ListingOut(**item) for item in items]


@router.get("/listings/{listing_id}", response_model=ListingOut)
async def details(listing_id: str, svc: ListingSvc):
    item = await svc.details(listing_id)
    if not item:
        raise HTTPException(status_code=404, detail="آگهی پیدا نشد")
    return ListingOut(**item)


@router.post("/listing-requests", response_model=ListingRequestOut, status_code=201)
async def submit_request(
    payload: ListingRequestIn,
    identity: IdentityDep,
    session: AsyncSession = Depends(get_session),
):
    """ثبت درخواست آگهی فقط برای کاربر لاگینشده — مطابق سند فاز ۳."""
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
        message="درخواست آگهی شما ثبت شد و در صف بررسی است. نتیجه از طریق حساب کاربری اطلاع داده میشود.",
    )
