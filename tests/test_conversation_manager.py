import json

import pytest

from app.ai.llm import FakeLLMClient, LLMResponse, Usage
from app.ai.orchestration import ConversationManager
from app.tools.base import Tool, ToolRegistry, ToolResult


def make_history(n: int):
    out = []
    for i in range(n):
        out.append({"role": "user", "content": f"سؤال {i}"})
        out.append({"role": "assistant", "content": f"جواب {i}"})
    return out


async def test_system_prompt_and_window():
    llm = FakeLLMClient(reply="پاسخ")
    mgr = ConversationManager(llm=llm, max_history=8)
    await mgr.reply(make_history(20) + [{"role": "user", "content": "آخری"}])

    msgs = llm.last_messages
    assert msgs[0]["role"] == "system"
    assert "BeautyBoss" in msgs[0]["content"]
    chat = [m for m in msgs if m["role"] != "system"]
    assert len(chat) <= 8
    assert chat[-1]["content"] == "آخری"
    assert chat[0]["role"] == "user"


async def test_empty_reply_fallback():
    class EmptyLLM(FakeLLMClient):
        async def chat(self, messages, **opts):
            return LLMResponse(content=None)

    mgr = ConversationManager(llm=EmptyLLM())
    resp = await mgr.reply([{"role": "user", "content": "سلام"}])
    assert resp.content
    assert "متأسفم" in (resp.content or "") or resp.content


async def test_tool_calling_loop():
    async def handler(args):
        return ToolResult(content=json.dumps({"ok": True, "q": args.get("query")}, ensure_ascii=False))

    tool = Tool(
        name="search_listings",
        description="جستجو",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        handler=handler,
    )
    reg = ToolRegistry()
    reg.register(tool)

    calls = []

    class ToolLLM(FakeLLMClient):
        async def chat(self, messages, **opts):
            calls.append({"n": self.chat_calls, "tools": opts.get("tools"), "msgs": messages})
            self.chat_calls += 1
            if len(calls) == 1:
                return LLMResponse(
                    content=None,
                    finish_reason="tool_calls",
                    tool_calls=[
                        {
                            "id": "call_1",
                            "function": {
                                "name": "search_listings",
                                "arguments": json.dumps({"query": "سالن"}, ensure_ascii=False),
                            },
                        }
                    ],
                )
            return LLMResponse(
                content="این نتیجه جستجو است.",
                usage=Usage(1, 1),
                finish_reason="stop",
            )

    llm = ToolLLM()
    mgr = ConversationManager(llm=llm, tools=reg)
    resp = await mgr.reply([{"role": "user", "content": "سالن می‌خواهم"}])

    assert resp.content == "این نتیجه جستجو است."
    assert len(calls) == 2
    # دور اول tools فرستاده شده
    assert calls[0]["tools"] and calls[0]["tools"][0]["function"]["name"] == "search_listings"
    # دور دوم پیام tool در تاریخچه است
    roles = [m["role"] for m in calls[1]["msgs"]]
    assert "tool" in roles


async def test_stream_yields_chunks():
    llm = FakeLLMClient(reply="سلام دنیا")
    mgr = ConversationManager(llm=llm)
    parts = [c async for c in mgr.stream([{"role": "user", "content": "سلام"}])]
    assert "".join(parts) == "سلام دنیا"
    assert len(parts) > 1  # تکه‌تکه
