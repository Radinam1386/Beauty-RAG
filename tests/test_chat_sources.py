import pytest

from app.ai.llm import FakeLLMClient, LLMResponse, Usage
from app.chat.service import ChatService
from tests.conftest import FakeChatRepository, make_identity
from app.knowledge.store import search_knowledge


async def test_send_message_knowledge_intent():
    repo = FakeChatRepository()
    llm = FakeLLMClient(reply="بر اساس راهنما، ضدآفتاب روزانه مهم است.")
    svc = ChatService(repository=repo, llm=llm)
    guest = make_identity(False, "g-k")
    conv = await svc.create_conversation(guest, title="پوست")
    result = await svc.send_message(guest, conv.id, "برای پوست خشک چه کرم مرطوبکننده‌ای خوب است؟")
    assert result.assistant_message.content
    assert result.sources  # intent knowledge
    assert result.listings in (None, [])


async def test_send_message_listing_intent():
    repo = FakeChatRepository()
    llm = FakeLLMClient(reply="این آگهیها را پیدا کردم.")
    svc = ChatService(repository=repo, llm=llm)
    guest = make_identity(False, "g-l")
    conv = await svc.create_conversation(guest)
    result = await svc.send_message(guest, conv.id, "دنبال رنگ و مش مو در تهران می‌گردم")
    assert result.listings
    assert any("مو" in (l.get("title") or "") for l in result.listings)
