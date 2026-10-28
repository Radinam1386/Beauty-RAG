import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    owner_type: Mapped[str] = mapped_column(String(10))
    external_user_id: Mapped[str | None] = mapped_column(String(64))
    guest_session_id: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(200))

    status: Mapped[str] = mapped_column(
        String(10),
        server_default=text("'active'"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.id",
    )

    __table_args__ = (
        CheckConstraint(
            "owner_type IN ('guest', 'user')",
            name="owner_type",
        ),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="status",
        ),
        CheckConstraint(
            "(owner_type = 'user' AND external_user_id IS NOT NULL "
            "AND guest_session_id IS NULL) OR "
            "(owner_type = 'guest' AND guest_session_id IS NOT NULL "
            "AND external_user_id IS NULL)",
            name="owner_consistent",
        ),
        Index(
            "ix_conversations_user_updated",
            "external_user_id",
            text("updated_at DESC"),
        ),
        Index(
            "ix_conversations_guest_session",
            "guest_session_id",
        ),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
    )

    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str | None] = mapped_column(Text)
    tool_calls: Mapped[list | None] = mapped_column(JSONB)
    tool_call_id: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    conversation: Mapped[Conversation] = relationship(
        back_populates="messages",
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('system', 'user', 'assistant', 'tool')",
            name="role",
        ),
        Index(
            "ix_messages_conversation_id_id",
            "conversation_id",
            "id",
        ),
    )