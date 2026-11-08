"""Chat API — فاز ۲ و ۴.

- POST /chat                                  شروع یا ادامه چت ذخیره‌شده
- GET/POST /conversations                     گفتگوهای متعلق به کاربر یا نشست مهمان
- GET  /conversations/{id}/messages
- POST /conversations/{id}/messages
- DELETE /conversations/{id}
- POST /conversations/{id}/messages/stream
"""

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.ai.llm.errors import LLMError
from app.api.dependencies import BudgetDep, ChatServiceDep
from app.api.v1.schemas.chat import (
    ChatIn,
    ChatOut,
    ConversationCreate,
    ConversationOut,
    ListingSummaryOut,
    MessageCreate,
    MessageOut,
    PaginatedConversations,
    SendMessageOut,
    SourceOut,
)
from app.auth.dependencies import IdentityDep
from app.chat.exceptions import (
    ChatError,
    ConversationAccessError,
    ConversationNotFound,
    EmptyMessageError,
    MessageTooLongError,
)
from app.core.config import get_settings
from app.limits import enforce_rate_limit

logger = logging.getLogger(__name__)

# دسترسی به هر گفتگو در ChatService و repository بر اساس مالک آن بررسی می‌شود.
router = APIRouter(tags=["Chat"])
public_router = APIRouter(tags=["Chat"])


def _chat_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ConversationNotFound):
        return HTTPException(status_code=404, detail="گفتگو پیدا نشد")
    if isinstance(exc, ConversationAccessError):
        return HTTPException(status_code=404, detail="گفتگو پیدا نشد")
    if isinstance(exc, EmptyMessageError):
        return HTTPException(status_code=422, detail="متن پیام خالی است")
    if isinstance(exc, MessageTooLongError):
        return HTTPException(status_code=422, detail="متن پیام بیش از حد مجاز است")
    if isinstance(exc, LLMError):
        logger.warning("LLM error: %s", type(exc).__name__)
        return HTTPException(status_code=502, detail="سرویس مدل زبانی در دسترس نیست")
    if isinstance(exc, OperationalError):
        logger.exception("DB connection error")
        return HTTPException(status_code=503, detail="سرویس دیتابیس در دسترس نیست")
    return HTTPException(status_code=500, detail="خطای داخلی")


def _listings_out(items: list | None) -> list[ListingSummaryOut] | None:
    return [ListingSummaryOut(**item) for item in items] if items else None


def _sources_out(items: list | None) -> list[SourceOut] | None:
    return [SourceOut(**item) for item in items] if items else None


@public_router.post("/chat", response_model=ChatOut)
async def chat(
    payload: ChatIn,
    request: Request,
    identity: IdentityDep,
    service: ChatServiceDep,
    budget: BudgetDep,
):
    """شروع یا ادامه گفتگو؛ پیام مهمان و کاربر هر دو ذخیره می‌شوند."""
    enforce_rate_limit(request, identity, get_settings())
    await budget.check()

    try:
        if payload.conversation_id is not None:
            result = await service.send_message(
                identity, payload.conversation_id, payload.content
            )
        else:
            conv = await service.create_conversation(identity)
            result = await service.send_message(identity, conv.id, payload.content)
    except (ChatError, LLMError, OperationalError) as exc:
        raise _chat_error(exc) from None
    except SQLAlchemyError:
        logger.exception("DB error on chat")
        raise HTTPException(status_code=500, detail="خطای ذخیره‌سازی") from None

    await budget.record(
        result.llm.usage.prompt_tokens, result.llm.usage.completion_tokens
    )
    return ChatOut(
        conversation_id=result.conversation.id,
        content=result.assistant_message.content or "",
        model=result.assistant_message.model,
        listings=_listings_out(result.listings),
        sources=_sources_out(result.sources),
    )


@router.get("/conversations", response_model=PaginatedConversations)
async def list_conversations(
    identity: IdentityDep,
    service: ChatServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=50, alias="pageSize"),
):
    items, total = await service.list_conversations(identity, page=page, page_size=page_size)
    size = page_size or service.settings.conversations_page_size
    pages = (total + size - 1) // size if size else 0
    return PaginatedConversations(
        items=[ConversationOut.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=size,
        pages=pages,
    )


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreate,
    identity: IdentityDep,
    service: ChatServiceDep,
):
    conv = await service.create_conversation(identity, title=payload.title)
    return ConversationOut.model_validate(conv)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: uuid.UUID,
    identity: IdentityDep,
    service: ChatServiceDep,
    limit: int | None = Query(default=None, ge=1, le=200),
):
    try:
        msgs = await service.get_messages(identity, conversation_id, limit=limit)
    except ConversationNotFound:
        raise HTTPException(status_code=404, detail="گفتگو پیدا نشد") from None
    out: list[MessageOut] = []
    for m in msgs:
        item = MessageOut.model_validate(m)
        tc = m.tool_calls
        if isinstance(tc, dict):
            if tc.get("listings"):
                item.listings = [ListingSummaryOut(**x) for x in tc["listings"]]
            if tc.get("sources"):
                item.sources = [SourceOut(**x) for x in tc["sources"]]
        out.append(item)
    return out


@router.post("/conversations/{conversation_id}/messages", response_model=SendMessageOut)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    request: Request,
    identity: IdentityDep,
    service: ChatServiceDep,
    budget: BudgetDep,
):
    enforce_rate_limit(request, identity, get_settings())
    await budget.check()
    try:
        result = await service.send_message(identity, conversation_id, payload.content)
    except (ChatError, LLMError, OperationalError) as exc:
        raise _chat_error(exc) from None
    except SQLAlchemyError:
        logger.exception("DB error on send")
        raise HTTPException(status_code=500, detail="خطای ذخیره‌سازی") from None

    await budget.record(
        result.llm.usage.prompt_tokens, result.llm.usage.completion_tokens
    )
    assistant = MessageOut.model_validate(result.assistant_message)
    if result.listings:
        assistant.listings = [ListingSummaryOut(**item) for item in result.listings]
    if result.sources:
        assistant.sources = [SourceOut(**item) for item in result.sources]
    return SendMessageOut(
        conversation_id=result.conversation.id,
        user_message=MessageOut.model_validate(result.user_message),
        assistant_message=assistant,
        sources=assistant.sources,
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    identity: IdentityDep,
    service: ChatServiceDep,
):
    try:
        await service.delete_conversation(identity, conversation_id)
    except ConversationNotFound:
        raise HTTPException(status_code=404, detail="گفتگو پیدا نشد") from None
    except ConversationAccessError:
        raise HTTPException(status_code=404, detail="گفتگو پیدا نشد") from None
    return None


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    request: Request,
    identity: IdentityDep,
    service: ChatServiceDep,
    budget: BudgetDep,
):
    """SSE: event=delta / done / error"""
    enforce_rate_limit(request, identity, get_settings())
    await budget.check()

    async def gen():
        try:
            async for kind, payload_obj in service.stream_reply(
                identity, conversation_id, payload.content
            ):
                if kind == "delta":
                    yield "event: delta\n"
                    yield f"data: {json.dumps({'content': payload_obj}, ensure_ascii=False)}\n\n"
                elif kind == "done":
                    msg = MessageOut.model_validate(payload_obj)
                    yield "event: done\n"
                    yield f"data: {msg.model_dump_json()}\n\n"
        except ConversationNotFound:
            yield "event: error\n"
            yield 'data: {"detail": "گفتگو پیدا نشد"}\n\n'
        except EmptyMessageError:
            yield "event: error\n"
            yield 'data: {"detail": "متن پیام خالی است"}\n\n'
        except LLMError:
            logger.warning("LLM stream failed")
            yield "event: error\n"
            yield 'data: {"detail": "سرویس مدل زبانی در دسترس نیست"}\n\n'
        except Exception:
            logger.exception("stream failed")
            yield "event: error\n"
            yield 'data: {"detail": "خطای داخلی"}\n\n'

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
