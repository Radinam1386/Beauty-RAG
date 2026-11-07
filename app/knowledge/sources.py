"""پایگاه منابع RAG — فایل‌های Markdown پوشه ``BeautyRAG_Sources``.

هر فایل یک منبع رسمی است (FDA، NIH/MedlinePlus، Cleveland Clinic، ECHA، منابع فارسی)
و در سرصفحه‌اش عنوان، لینک، دسته، زبان و خلاصه آمده است. فایل به قطعه‌های Markdown
شکسته می‌شود تا جستجو دقیق باشد و هر نتیجه لینک واقعی منبع را داشته باشد.

بدون pgvector و بدون embedding: جستجوی کلمه‌ای + یک نقشهٔ کوچک معادل فارسی/انگلیسی،
چون بیشتر متن‌ها انگلیسی‌اند و سؤال کاربر فارسی است.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SOURCES_DIR = Path(__file__).resolve().parents[2] / "BeautyRAG_Sources"
CHUNK_CHARS = 1000
CONTENT_CHARS = 1200
FULL_CHARS = 6000
MAX_RESULTS = 6

ZWNJ = "\u200c"

CATEGORY_LABELS = {
    "01_cosmetics_makeup": "لوازم آرایشی",
    "02_skincare_personal_care": "مراقبت پوست و بهداشت",
    "03_haircare_scalp": "مو و پوست سر",
    "04_ingredients_safety": "ترکیبات و ایمنی",
    "05_regulations_standards": "قوانین و استانداردها",
    "06_persian_resources": "منابع فارسی",
}

# معادل‌های فارسی → انگلیسی برای اینکه سؤال فارسی، منابع انگلیسی را پیدا کند.
EXPANSIONS: dict[str, list[str]] = {
    "پوست": ["skin", "dermat"],
    "پوستی": ["skin"],
    "ضد": ["anti"],
    "ضدافتاب": ["sunscreen", "sun", "spf"],
    "افتاب": ["sun", "sunscreen", "spf"],
    "کرم": ["cream", "sunscreen"],
    "مو": ["hair", "scalp"],
    "موی": ["hair"],
    "سر": ["scalp", "head"],
    "ریزش": ["hair", "loss", "alopecia", "thinning"],
    "کاشت": ["transplant", "nail"],
    "ناخن": ["nail"],
    "میکاپ": ["makeup", "cosmetic"],
    "ارایش": ["makeup", "cosmetic"],
    "ارایشی": ["cosmetic"],
    "بهداشتی": ["hygien", "personal", "care"],
    "جوش": ["acne", "pimple"],
    "اکنه": ["acne"],
    "مرطوب": ["moisturizer", "moisturizing", "hydration"],
    "پیری": ["aging", "wrinkle"],
    "چروک": ["wrinkle", "aging"],
    "لک": ["pigmentation", "spot"],
    "تیره": ["pigmentation", "dark"],
    "حساسیت": ["allergy", "sensitive", "irritation"],
    "پچ": ["patch"],
    "تست": ["test", "patch"],
    "رنگ": ["color", "dye"],
    "مش": ["highlight", "bleach"],
    "هایلایت": ["highlight"],
    "بالیاژ": ["balayage", "highlight"],
    "کراتین": ["keratin", "protein"],
    "شامپو": ["shampoo"],
    "سولفات": ["sulfate"],
    "پارابن": ["paraben"],
    "ویتامین": ["vitamin"],
    "رتینول": ["retinol", "retinoid"],
    "اسید": ["acid", "aha", "bha"],
    "تالک": ["talc"],
    "تاریخ": ["expiration", "shelf", "date"],
    "انقضا": ["expiration", "shelf", "life"],
    "اصالت": ["authenticity", "counterfeit", "fake"],
    "تقلب": ["counterfeit", "fake"],
    "مجاز": ["authorized", "unauthorized", "regulation"],
    "غیرمجاز": ["unauthorized", "counterfeit"],
    "قانون": ["regulation", "law", "mocra"],
    "مقررات": ["regulation", "standards"],
    "ترکیبات": ["ingredients", "inci"],
    "ترکیب": ["ingredient"],
    "ایمنی": ["safety", "safe"],
    "خطر": ["risk", "safety", "warning"],
    "خشک": ["dry", "dryness"],
    "خشکی": ["dry"],
    "چرب": ["oily", "oil"],
    "منافذ": ["pore", "pores"],
    "روشن": ["brightening", "lightening"],
    "لوسیون": ["lotion"],
    "مژه": ["eyelash", "lash"],
    "ابرو": ["eyebrow"],
    "چشم": ["eye"],
    "لب": ["lip"],
    "محصول": ["product", "cosmetic"],
    "مواد": ["ingredient", "product"],
    "سرطان": ["cancer", "risk"],
    "اکنه": ["acne"],
    "روزاسه": ["rosacea"],
    "اگزما": ["eczema"],
    "پوست‌سر": ["scalp"],
}

META_RE = re.compile(r"^-\s*([^:]+):\s*(.+)$")
URL_RE = re.compile(r"https?://[^\s)\]>]+")

NOISE_PREFIXES = (
    "Skip to main content",
    "Official websites use .gov",
    "Secure .gov websites use HTTPS",
    "Share sensitive information only",
    "A .gov website belongs",
    "TIMESTAMPS",
    "About this capture",
    "The Wayback Machine",
    "You Are Here:",
    "URL of this page:",
    "- Skip to",
    "A lock (",
)


@dataclass(frozen=True)
class SourceChunk:
    id: str
    title: str
    content: str
    full: str
    source: str
    url: str
    language: str
    category: str
    title_hay: str
    body_hay: str


def normalize(text: str) -> str:
    value = (text or "").replace(ZWNJ, " ").replace("ي", "ی").replace("ك", "ک")
    value = value.replace("آ", "ا").replace("أ", "ا").replace("إ", "ا")
    value = re.sub(r"[\u064B-\u0652]", "", value)
    return re.sub(r"\s+", " ", value).lower().strip()


def _clean(body: str) -> str:
    lines: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or len(line) < 2:
            continue
        if any(line.startswith(prefix) for prefix in NOISE_PREFIXES):
            continue
        if re.fullmatch(r"[\d\s\-–—:/]+", line):
            continue
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _pack(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= limit:
        return [text] if text else []

    pieces: list[str] = []
    buffer = ""
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(buffer) + len(paragraph) + 2 <= limit:
            buffer = f"{buffer}\n\n{paragraph}".strip()
            continue
        if buffer:
            pieces.append(buffer)
        while len(paragraph) > limit:
            pieces.append(paragraph[:limit])
            paragraph = paragraph[limit:]
        buffer = paragraph
    if buffer:
        pieces.append(buffer)
    return pieces


def _split_sections(body: str) -> list[tuple[str, str]]:
    """بدنه را بر اساس تیترهای Markdown به قطعه‌های کوچک می‌شکند."""
    sections: list[tuple[str, str]] = []
    for section in re.split(r"\n(?=#{1,3} )", body):
        section = section.strip()
        if not section:
            continue
        heading = ""
        if section.startswith("#"):
            first, _, rest = section.partition("\n")
            heading = first.lstrip("# ").strip()
            section = rest.strip()
        for piece in _pack(section):
            if len(piece) >= 60:
                sections.append((heading, piece))
    return sections


def _parse_file(path: Path) -> list[SourceChunk]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("خواندن منبع %s شکست خورد: %s", path.name, exc)
        return []

    lines = text.splitlines()
    doc_title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("# ")), path.stem)

    meta: dict[str, str] = {}
    body_start = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        match = META_RE.match(stripped)
        if match and index < 25:
            meta.setdefault(match.group(1).strip(), match.group(2).strip())
        if stripped.startswith("## متن اصلی"):
            body_start = index + 1
            break
    else:
        body_start = 0
        for index, line in enumerate(lines):
            if line.startswith("## ") and index > 3:
                body_start = index
                break

    source_field = meta.get("منبع", "")
    url_match = URL_RE.search(source_field) or URL_RE.search(text)
    url = url_match.group(0) if url_match else ""
    language = meta.get("زبان", "").strip() or "en"
    category = CATEGORY_LABELS.get(path.parent.name, path.parent.name)

    chunks: list[SourceChunk] = []
    for number, (heading, piece) in enumerate(_split_sections(_clean("\n".join(lines[body_start:]))), 1):
        title = f"{doc_title} — {heading}" if heading else doc_title
        chunks.append(
            SourceChunk(
                id=f"{path.stem}-{number}",
                title=title,
                content=piece[:CONTENT_CHARS],
                full=piece[:FULL_CHARS],
                source=doc_title,
                url=url,
                language=language,
                category=category,
                title_hay=normalize(f"{doc_title} {heading}"),
                body_hay=normalize(piece),
            )
        )
    return chunks


@lru_cache(maxsize=1)
def load_chunks() -> tuple[SourceChunk, ...]:
    if not SOURCES_DIR.is_dir():
        logger.warning("پوشه منابع RAG پیدا نشد: %s", SOURCES_DIR)
        return ()

    chunks: list[SourceChunk] = []
    files = sorted(SOURCES_DIR.rglob("*.md"))
    for path in files:
        if path.name.lower() == "readme.md":
            continue
        chunks.extend(_parse_file(path))
    logger.info("منابع RAG: %d فایل، %d قطعه.", len(files), len(chunks))
    return tuple(chunks)


def _query_terms(query: str) -> list[str]:
    terms: list[str] = []
    for token in re.findall(r"[0-9a-z\u0600-\u06FF_]+", normalize(query)):
        if len(token) < 2:
            continue
        terms.append(token)
        terms.extend(EXPANSIONS.get(token, []))
        if token.endswith("s") and len(token) > 4:
            terms.append(token[:-1])
    return list(dict.fromkeys(terms))


def _as_dict(chunk: SourceChunk, full: bool = False) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "title": chunk.title,
        "content": chunk.full if full else chunk.content,
        "source": chunk.source,
        "url": chunk.url,
        "language": chunk.language,
        "category": chunk.category,
    }


def search_sources(query: str, limit: int = MAX_RESULTS) -> list[dict[str, Any]]:
    terms = _query_terms(query)
    if not terms:
        return []

    scored: list[tuple[int, SourceChunk]] = []
    for chunk in load_chunks():
        score = 0
        for term in terms:
            if term in chunk.title_hay:
                score += 3
            elif term in chunk.body_hay:
                score += 1
        if score:
            scored.append((score, chunk))

    scored.sort(key=lambda pair: (-pair[0], pair[1].id))

    # از هر تیتر فقط بهترین قطعه را نگه می‌داریم تا نتیجه تکراری نباشد
    seen: set[str] = set()
    picked: list[SourceChunk] = []
    for _, chunk in scored:
        if chunk.title in seen:
            continue
        seen.add(chunk.title)
        picked.append(chunk)
        if len(picked) >= limit:
            break
    return [_as_dict(chunk) for chunk in picked]


def get_source(chunk_id: str) -> dict[str, Any] | None:
    for chunk in load_chunks():
        if chunk.id == chunk_id:
            return _as_dict(chunk, full=True)
    return None
