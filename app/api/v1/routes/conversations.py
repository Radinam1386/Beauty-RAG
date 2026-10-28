import secrets

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Conversation
from app.database.session import get_session
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
)


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=201,
)
async def create_conversation(
    data: ConversationCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    guest_session_id = request.cookies.get("beauty_rag_guest")

    if not guest_session_id or len(guest_session_id) != 43:
        guest_session_id = secrets.token_urlsafe(32)

        response.set_cookie(
            key="beauty_rag_guest",
            value=guest_session_id,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )

    conversation = Conversation(
        owner_type="guest",
        guest_session_id=guest_session_id,
        title=data.title,
    )

    session.add(conversation)

    await session.commit()
    await session.refresh(conversation)

    return conversation