from dataclasses import replace

from app.ai.llm import LLMClient, LLMResponse, Message
from app.ai.memory.manager import build_messages

EMPTY_REPLY = "متأسفم، نتوانستم پاسخی آماده کنم. لطفاً دوباره امتحان کنید."


async def generate_reply(
    llm: LLMClient,
    history: list[Message],
    **opts,
):
    messages = build_messages(history)
    response = await llm.chat(messages, **opts)

    if not response.content:
        response = replace(response, content=EMPTY_REPLY)
    return response