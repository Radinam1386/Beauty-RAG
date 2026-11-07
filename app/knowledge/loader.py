"""بارگذاری دانش ثابت — فاز ۳.

همه فایل‌های Markdown پوشه ``knowledge/`` (به ترتیب نام فایل) یک بار خوانده و به یک
متن واحد تبدیل می‌شوند تا در system prompt قرار بگیرد. اگر پوشه یا فایل نبود، برنامه
نباید crash کند؛ فقط متن خالی و warning برمی‌گردد.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_KNOWLEDGE_CHARS = 20_000
KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"


@lru_cache(maxsize=4)
def _read_all(knowledge_dir: str) -> str:
    base = Path(knowledge_dir)
    if not base.is_dir():
        logger.warning("پوشه دانش پیدا نشد: %s — دانش خالی در نظر گرفته می‌شود.", base)
        return ""

    files = sorted(p for p in base.glob("*.md") if p.is_file())
    if not files:
        logger.warning("هیچ فایل .md در پوشه دانش نیست: %s", base)
        return ""

    parts: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("خواندن فایل دانش %s شکست خورد: %s", path.name, exc)
            continue
        if text:
            # نام فایل نگه داشته می‌شود تا در مرحله B به منبع chunk تبدیل شود
            parts.append(f"<!-- source: {path.name} -->\n{text}")

    knowledge = "\n\n".join(parts)
    logger.info("دانش سایت: %d فایل، %d کاراکتر.", len(parts), len(knowledge))
    if len(knowledge) > MAX_KNOWLEDGE_CHARS:
        logger.warning(
            "دانش بزرگ شده (%d کاراکتر > %d)؛ وقت مناسبی برای RAG (مرحله B) است.",
            len(knowledge),
            MAX_KNOWLEDGE_CHARS,
        )
    return knowledge


def load_knowledge(knowledge_dir: str | Path | None = None) -> str:
    """متن کامل دانش. نتیجه cache می‌شود، پس خواندن مکرر هزینه‌ای ندارد."""
    return _read_all(str(knowledge_dir or KNOWLEDGE_DIR))
