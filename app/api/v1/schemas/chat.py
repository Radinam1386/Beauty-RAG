"""قرارداد API چت — هم‌راستا با مدل‌های فرانت‌اند (camelCase)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ConversationOut(CamelModel):
    id: uuid.UUID
    title: str | None
    owner_type: str
    status: str
    created_at: datetime
    updated_at: datetime


class PaginatedConversations(CamelModel):
    items: list[ConversationOut]
    total: int
    page: int
    page_size: int
    pages: int


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("متن پیام خالی است")
        return v


class SourceOut(CamelModel):
    title: str
    url: str | None = None


class ListingSummaryOut(CamelModel):
    id: str
    title: str
    categoryId: str
    categoryName: str
    city: str
    area: str | None = None
    priceLabel: str | None = None
    providerName: str | None = None
    url: str | None = None
    isSample: bool = False


class MessageOut(CamelModel):
    id: int
    role: str
    content: str | None
    model: str | None
    created_at: datetime
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None
    listings: list[ListingSummaryOut] | None = None
    sources: list[SourceOut] | None = None


class SendMessageOut(CamelModel):
    """خروجی ارسال پیام: پیام کاربر + پاسخ دستیار."""

    conversation_id: uuid.UUID
    user_message: MessageOut
    assistant_message: MessageOut
