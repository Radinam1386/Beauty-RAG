from app.ai.llm import Message
from app.ai.prompts.system import build_system_prompt

MAX_HISTORY = 5


def build_messages(
    history: list[Message],
    system_prompt: str | None = None,
    max_messages: int = MAX_HISTORY,
):
    chat = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m["role"] in ("user", "assistant") and m.get("content")
    ]

    chat = chat[-max_messages:]

    while chat and chat[0]["role"] != "user":
        chat.pop(0)

    system = {"role": "system", "content": system_prompt or build_system_prompt()}
    return [system] + chat