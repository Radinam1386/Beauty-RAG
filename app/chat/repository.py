"""لایه دسترسی به داده گفتگو و پیام.

همه کوئری‌ها مالکیت را در WHERE اعمال می‌کنند تا نشت داده بین مهمان/کاربر پیش نیاید.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.identity import Identity
from app.database.models import Conversation, Message


def _owner_filter(identity: Identity):
    if identity.is_user:
        return (
            Conversation.owner_type == "user",
            Conversation.external_user_id == identity.external_user_id,
        )
    return (
        Conversation.owner_type == "guest",
        Conversation.guest_session_id == identity.guest_session_id,
    )


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_conversation(self, identity: Identity, title: str | None = None) -> Conversation:
        conv = Conversation(
            owner_type=identity.owner_type,
            external_user_id=identity.external_user_id,
            guest_session_id=identity.guest_session_id,
            title=(title or None),
            status="active",
        )
        self.session.add(conv)
        await self.session.commit()
        await self.session.refresh(conv)
        return conv

    async def get_conversation(
        self,
        identity: Identity,
        conversation_id: uuid.UUID,
        *,
        include_archived: bool = False,
    ) -> Conversation | None:
        filters = [
            Conversation.id == conversation_id,
            *_owner_filter(identity),
        ]
        if not include_archived:
            filters.append(Conversation.status == "active")
        stmt = select(Conversation).where(*filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        identity: Identity,
        page: int = 1,
        page_size: int = 20,
        status: str = "active",
    ) -> tuple[list[Conversation], int]:
        stmt = (
            select(Conversation)
            .where(*_owner_filter(identity), Conversation.status == status)
            .order_by(Conversation.updated_at.desc())
        )
        count_stmt = select(func.count()).select_from(Conversation).where(
            *_owner_filter(identity),
            Conversation.status == status,
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows), int(total)

    async def add_message(self, conversation: Conversation, **fields) -> Message:
        msg = Message(conversation_id=conversation.id, **fields)
        self.session.add(msg)
        # لمس updated_at گفتگو برای فهرست «آخرین»ها
        await self.session.flush()
        return msg

    async def touch_conversation(self, conversation: Conversation, title: str | None = None) -> None:
        if title is not None:
            conversation.title = title
        conversation.updated_at = func.now()
        await self.session.flush()

    async def list_messages(
        self,
        conversation: Conversation,
        limit: int | None = None,
        order_desc: bool = False,
    ) -> list[Message]:
        stmt = select(Message).where(Message.conversation_id == conversation.id)
        if order_desc:
            stmt = stmt.order_by(Message.id.desc())
        else:
            stmt = stmt.order_by(Message.id.asc())
        if limit is not None:
            # آخرین N پیام در ترتیب طبیعی
            if order_desc:
                stmt = stmt.limit(limit)
            else:
                sub = (
                    select(Message.id)
                    .where(Message.conversation_id == conversation.id)
                    .order_by(Message.id.desc())
                    .limit(limit)
                )
                stmt = (
                    select(Message)
                    .where(Message.conversation_id == conversation.id, Message.id.in_(sub))
                    .order_by(Message.id.asc())
                )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)

    async def count_messages(self, conversation: Conversation) -> int:
        stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation.id)
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def archive_conversation(self, conversation: Conversation) -> None:
        conversation.status = "archived"
        await self.session.commit()

    async def delete_conversation(self, conversation: Conversation) -> None:
        await self.session.delete(conversation)
        await self.session.commit()

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, obj) -> None:
        await self.session.refresh(obj)


    async def save_listing_request(self, **fields) -> None:
        from app.database.models import ListingRequest
        self.session.add(ListingRequest(**fields))
        await self.session.commit()
