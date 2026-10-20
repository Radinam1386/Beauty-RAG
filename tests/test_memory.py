from app.ai.llm import FakeLLMClient, LLMResponse
from app.ai.memory.manager import build_messages
from app.ai.orchestration.chat import EMPTY_REPLY, generate_reply


def msg(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def test_system_prompt_is_first():
    result = build_messages([msg("user", "سلام")])
    assert result[0]["role"] == "system"
    assert result[1] == msg("user", "سلام")


def test_keeps_only_last_messages_and_starts_with_user():
    history = []
    for i in range(10):
        history.append(msg("user", f"سؤال {i}"))
        history.append(msg("assistant", f"جواب {i}"))
    history.append(msg("user", "آخرین سؤال"))

    result = build_messages(history, max_messages=4)
    chat = result[1:]  # بدون system

    assert chat[0]["role"] == "user"
    assert chat[-1]["content"] == "آخرین سؤال"
    assert len(chat) <= 4


def test_ignores_empty_and_non_chat_messages():
    history = [
        msg("user", "سلام"),
        msg("assistant", ""),
        msg("tool", "داده ابزار"),
    ]
    result = build_messages(history)
    assert [m["role"] for m in result] == ["system", "user"]


async def test_generate_reply():
    response = await generate_reply(FakeLLMClient(), [msg("user", "سلام")])
    assert response.content


async def test_empty_reply_gets_fallback():
    class EmptyLLM(FakeLLMClient):
        async def chat(self, messages, **opts):
            return LLMResponse(content=None)

    response = await generate_reply(EmptyLLM(), [msg("user", "سلام")])
    assert response.content == EMPTY_REPLY