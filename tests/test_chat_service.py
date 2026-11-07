import pytest

from app.ai.llm import FakeLLMClient, LLMResponse, Usage
from app.auth.identity import Identity
from app.chat.exceptions import ConversationNotFound, EmptyMessageError
from app.chat.service import ChatService
from tests.conftest import FakeChatRepository, make_identity


async def test_create_and_list_isolated_per_owner():
    repo = FakeChatRepository()
    svc = ChatService(repository=repo, llm=FakeLLMClient())
    guest = make_identity(user=False, key="g1")
    user = make_identity(user=True, key="u1")

    await svc.create_conversation(guest, title="مهمان")
    await svc.create_conversation(user, title="کاربر")

    g_items, g_total = await svc.list_conversations(guest)
    u_items, u_total = await svc.list_conversations(user)

    assert g_total == 1
    assert u_total == 1
    assert g_items[0].title == "مهمان"
    assert u_items[0].title == "کاربر"
    assert g_items[0].owner_type == "guest"
    assert u_items[0].owner_type == "user"


async def test_send_message_persists_history_and_auto_title():
    repo = FakeChatRepository()
    llm = FakeLLMClient(reply="پاسخ مدل")
    svc = ChatService(repository=repo, llm=llm)
    guest = make_identity(user=False, key="g1")
    conv = await svc.create_conversation(guest)

    result = await svc.send_message(guest, conv.id, "سلام، چطور می‌توانی کمک کنی؟")

    assert result.assistant_message.content == "پاسخ مدل"
    assert result.user_message.role == "user"
    assert result.assistant_message.role == "assistant"
    assert conv.title  # عنوان خودکار
    assert "سلام" in (conv.title or "")
    msgs = await svc.get_messages(guest, conv.id)
    assert [m.role for m in msgs] == ["user", "assistant"]
    # آخرین پیام فرستاده‌شده به مدل، پیام کاربر است
    assert llm.last_messages[-1]["role"] == "user"
    assert llm.last_messages[0]["role"] == "system"
    assert [m["content"] for m in llm.last_messages if m["role"] == "user"] == [
        "سلام، چطور می‌توانی کمک کنی؟"
    ]


async def test_history_window_is_limited():
    repo = FakeChatRepository()
    llm = FakeLLMClient(reply="ok")
    svc = ChatService(repository=repo, llm=llm)
    # پنجره پیش‌فرض ۸ است
    assert svc.settings.chat_history_limit == 8
    guest = make_identity(False, "g1")
    conv = await svc.create_conversation(guest)

    for i in range(12):
        await svc.send_message(guest, conv.id, f"سؤال {i}")

    # آخرین فراخوانی: system + حداکثر ۸ پیام
    assert llm.last_messages is not None
    chat = [m for m in llm.last_messages if m["role"] != "system"]
    assert len(chat) <= 8
    assert chat[-1]["content"] == "سؤال 11"
    assert chat[0]["role"] == "user"


async def test_guest_cannot_read_user_conversation():
    repo = FakeChatRepository()
    svc = ChatService(repository=repo, llm=FakeLLMClient())
    user = make_identity(True, "u1")
    guest = make_identity(False, "g1")
    conv = await svc.create_conversation(user, title="خصوصی")

    with pytest.raises(ConversationNotFound):
        await svc.get_messages(guest, conv.id)

    # مهمان دیگر هم نمی‌بیند
    other = make_identity(False, "g2")
    with pytest.raises(ConversationNotFound):
        await svc.get_messages(other, conv.id)


async def test_delete_archives_and_hides():
    repo = FakeChatRepository()
    svc = ChatService(repository=repo, llm=FakeLLMClient())
    guest = make_identity(False, "g1")
    conv = await svc.create_conversation(guest)
    await svc.delete_conversation(guest, conv.id)
    items, total = await svc.list_conversations(guest)
    assert total == 0
    with pytest.raises(ConversationNotFound):
        await svc.get_messages(guest, conv.id)


async def test_empty_message_rejected():
    repo = FakeChatRepository()
    svc = ChatService(repository=repo, llm=FakeLLMClient())
    guest = make_identity(False, "g1")
    conv = await svc.create_conversation(guest)
    with pytest.raises(EmptyMessageError):
        await svc.send_message(guest, conv.id, "   ")


async def test_pagination():
    repo = FakeChatRepository()
    svc = ChatService(repository=repo, llm=FakeLLMClient())
    guest = make_identity(False, "g1")
    for i in range(7):
        await svc.create_conversation(guest, title=f"گفتگو {i}")

    items, total = await svc.list_conversations(guest, page=1, page_size=3)
    assert total == 7
    assert len(items) == 3
    items2, _ = await svc.list_conversations(guest, page=3, page_size=3)
    assert len(items2) == 1
