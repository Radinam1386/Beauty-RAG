from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ListingCategoryOut(CamelModel):
    id: str
    name: str


class ListingOut(CamelModel):
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


class ListingSearchIn(CamelModel):
    query: str = Field(default="", max_length=200)
    categoryId: str | None = Field(default=None, max_length=64)
    city: str | None = Field(default=None, max_length=64)


class ListingRequestIn(CamelModel):
    categoryId: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    city: str = Field(min_length=2, max_length=64)
    area: str | None = Field(default=None, max_length=64)
    budgetLabel: str | None = Field(default=None, max_length=64)
    contactPhone: str = Field(min_length=10, max_length=15)
    conversationId: uuid.UUID | None = None


class ListingRequestOut(CamelModel):
    id: str
    status: str
    message: str
