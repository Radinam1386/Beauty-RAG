from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from pydantic.alias_generators import to_camel

from app.api.v1.schemas.listings import CamelModel
from app.knowledge.service import KnowledgeService

router = APIRouter(tags=["Knowledge"])


class KnowledgeHitOut(CamelModel):
    id: str
    title: str
    content: str
    source: str
    url: str | None = None


def get_knowledge_service() -> KnowledgeService:
    return KnowledgeService()


KnowledgeSvc = Annotated[KnowledgeService, Depends(get_knowledge_service)]


@router.get("/knowledge/search", response_model=list[KnowledgeHitOut])
async def search(
    svc: KnowledgeSvc,
    q: str = Query(min_length=1, max_length=200),
):
    items = await svc.search(q)
    return [KnowledgeHitOut(**item) for item in items]


@router.get("/knowledge/{article_id}", response_model=KnowledgeHitOut)
async def article(article_id: str, svc: KnowledgeSvc):
    item = await svc.article(article_id)
    if not item:
        raise HTTPException(status_code=404, detail="مقاله پیدا نشد")
    return KnowledgeHitOut(**item)
