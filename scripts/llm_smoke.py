import asyncio

from app.ai.llm import create_llm_client


async def main() -> None:
    client = create_llm_client()
    try:
        response = await client.chat(
            [{"role": "user", "content": "سلام! در یک جمله بگو مراقبت از پوست چرا مهم است؟"}],
            max_tokens=15000,
        )
        print("پاسخ:", response.content)
        print("مدل:", response.model)
        print("توکن‌ها:", response.usage)
        print("زمان (ms):", response.latency_ms)
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())