# BeautyBoss AI

سرویس هوش مصنوعی BeautyBoss (Python / FastAPI / PostgreSQL + pgvector) که کنار بکاند Spring Boot اجرا می‌شود.

این فایل می‌گوید پروژه را چطور اجرا کنید و **قبل از شروع کار** چه کارهایی باید انجام شود.

---

## اجرای مستقل برای تست چت

بعد از نصب وابستگی‌های Python و Node و تنظیم `.env`، PostgreSQL را روشن کنید و از ریشه پروژه اجرا کنید:

```bash
./start-dev.sh
```

سپس [صفحه چت](http://localhost:4200/chat) را باز کنید. برای تست نیازی به اتصال یا ورود به سایت اصلی نیست. اسکریپت migrationها را اجرا می‌کند و فرانت‌اند و بک‌اند را بالا می‌آورد؛ با `Ctrl+C` متوقف می‌شود. اگر PostgreSQL را با Docker اجرا می‌کنید، ابتدا `docker compose up -d db` را بزنید و مطمئن شوید `DATABASE_URL` به همان دیتابیس اشاره می‌کند.

برای پاسخ واقعی، `LLM_USE_FAKE=false` و آدرس، مدل و کلید معتبر LLM را در `.env` تنظیم کنید. با `LLM_USE_FAKE=true` می‌توان بدون سرویس مدل، اتصال را با یک پاسخ ثابت آزمایشی بررسی کرد. تغییر `.env` نیاز به راه‌اندازی مجدد بک‌اند دارد.

گفتگوهای مهمان با شناسه نشست مرورگر در دیتابیس ذخیره می‌شوند و پس از تازه‌سازی دوباره نمایش داده می‌شوند. برای بازیابی در همان مرورگر، داده‌های سایت را پاک نکنید. هنگام اتصال به سایت، آدرس API فرانت‌اند در `frontend/src/app/core/environment.ts` و `CORS_ORIGINS` بک‌اند باید با نشانی استقرار هماهنگ شوند.

---

## ۱. پیش‌نیازها

- Python (هر دو نفر **یک نسخه** استفاده کنید؛ سند پروژه ۳.۱۲ یا ۳.۱۳ را پیشنهاد می‌کند)
- Docker Desktop
- Git

---

## ۲. راه‌اندازی بار اول (هر نفر، یک بار)

```bash
# ۱. کلون پروژه
git clone <آدرس-ریپو>
cd Beauty-RAG

# ۲. محیط مجازی
python -m venv env
source env/bin/activate        # ویندوز: env\Scripts\activate

# ۳. نصب وابستگی‌ها (از ریشه پروژه، کنار pyproject.toml)
pip install -e ".[dev]"

# ۴. ساخت فایل تنظیمات
cp .env.example .env
```

بعد فایل `.env` را باز کن و پر کن:

- `POSTGRES_PASSWORD` و رمز داخل `DATABASE_URL` **باید دقیقاً یکی باشند**.
- رمز را فعلاً فقط حروف و عدد بگذار (کاراکتر مثل `@ : / # %` داخل URL مشکل می‌سازد).
- `LLM_BASE_URL` و `LLM_API_KEY` و `LLM_MODEL` را از هم‌تیمی یا مدیر پروژه بگیر. **کلید API را هرگز commit نکن.** `.env` در `.gitignore` است.

```bash
# ۵. بالا آوردن دیتابیس
docker compose up -d db
docker compose ps              # باید healthy باشد

# ۶. ساخت جدول‌ها
alembic upgrade head
```

### چک نهایی

```bash
docker compose exec db psql -U beautyboss -d beautyboss -c "\dt"
docker compose exec db psql -U beautyboss -d beautyboss -c "SELECT extname FROM pg_extension WHERE extname='vector';"
```

باید جدول‌های `conversations`، `messages` و `alembic_version` و extension به نام `vector` را ببینی.

---

## ۳. کارهای هر روز (قبل از شروع کار)

هر بار که کار را شروع می‌کنی، به این ترتیب:

```bash
source env/bin/activate        # فعال‌کردن env
git checkout main
git pull                       # آخرین تغییرها
pip install -e ".[dev]"        # اگر وابستگی جدید اضافه شده باشد
docker compose up -d db        # دیتابیس روشن باشد
alembic upgrade head           # ← مهم: migrationهای جدید را اجرا کن
git checkout -b feature/اسم-کار
```

> **قاعده طلایی:** بعد از هر `git pull` یک بار `alembic upgrade head` بزن. اگر هم‌تیمی‌ات migration جدید commit کرده باشد، دیتابیس تو را به‌روز می‌کند. اگر نزنی، کد جدید با جدول‌های قدیمی اجرا می‌شود و ارورهای عجیب می‌گیری.

---

## ۴. مخصوص نفر اول (Platform & Site Integration)

اگر تازه به پروژه اضافه شده‌ای یا بعد از چند روز برمی‌گردی:

1. **`git pull` و `pip install -e ".[dev]"`** (وابستگی‌های جدید از سمت نفر دوم می‌آید)
2. **`cp .env.example .env`** اگر هنوز نداری، و آن را پر کن. برای توسعه **نیازی به کلید واقعی LLM نداری**، چون `FakeLLMClient` (در `app/ai/llm/fake.py`، قدم ۴) آماده می‌شود و endpointهای چت را بدون هزینه تست می‌کنی.
3. **`docker compose up -d db`** و بعد **`alembic upgrade head`**
4. **`docker-compose.yml` مال توست.** سرویس `db` از طرف نفر دوم اضافه شده. وقتی سرویس FastAPI را اضافه می‌کنی، این را بگذار تا منتظر دیتابیس بماند:
   ```yaml
   depends_on:
     db:
       condition: service_healthy
   ```
5. **از `get_session` استفاده کن** (`app/database/session.py`) به‌عنوان dependency مشترک:
   ```python
   from fastapi import Depends
   from sqlalchemy.ext.asyncio import AsyncSession
   from app.database.session import get_session

   async def endpoint(session: AsyncSession = Depends(get_session)): ...
   ```
6. **مدل‌های `Conversation` و `Message`** ورودی کار توست در فاز ۲. قبل از ساختن API چت، یک بار با نفر دوم مرورشان کن، مخصوصاً:
   - فرمت `guest_session_id` (فعلاً `String(64)`)
   - نوع `external_user_id` (فعلاً `String(64)`، سازگار با شناسه عددی Spring)
   - قانون مالکیت: کاربر لاگین‌شده حتماً `external_user_id` دارد و مهمان حتماً `guest_session_id`. دیتابیس این را با CheckConstraint اجبار می‌کند.

---

## ۵. مخصوص نفر دوم (AI & Knowledge)

- مالک `app/database/` (مشترک)، `app/ai/` و `app/products/`.
- هر تغییری در `models.py` یعنی یک migration جدید (بخش ۶).
- بعد از ساخت `FakeLLMClient`، اطلاع بده تا نفر اول از آن استفاده کند.

---

## ۶. کار با Migration (Alembic)

Alembic مثل گیت برای ساختار دیتابیس است.

| دستور | کار |
|---|---|
| `alembic upgrade head` | همه migrationها را اجرا کن |
| `alembic downgrade -1` | آخرین migration را برگردان |
| `alembic downgrade base` | همه را برگردان (دیتابیس خالی) |
| `alembic current` | دیتابیس الان روی کدام نسخه است |
| `alembic history` | فهرست migrationها |

### وقتی مدل را تغییر دادی

```bash
alembic upgrade head                                   # اول دیتابیس به‌روز باشد
alembic revision --autogenerate -m "توضیح کوتاه"       # فقط یک بار
# فایل ساخته‌شده در migrations/versions/ را بخوان و بررسی کن
alembic upgrade head
alembic downgrade -1 && alembic upgrade head           # تست رفت و برگشت
git add migrations/versions/ && git commit
```

### قوانین مهم

- **`revision` را دو بار پشت هم نزن.** اگر دیتابیس به‌روز نباشد ارور «Target database is not up to date» می‌گیری.
- **فایل autogenerate را همیشه بخوان.** همیشه درست نیست (مثلاً ایندکس جا افتاده یا تکراری).
- **migrationی که merge شده را ویرایش نکن.** برای تغییر، یک migration جدید بساز.
- **دو نفر همزمان migration نسازید.** اگر هر دو از یک نسخه شروع کنید، Alembic دو «head» پیدا می‌کند. قبل از ساختن migration جدید `git pull` بزن و در گروه اطلاع بده. اگر conflict شد: `alembic merge heads -m "merge"`.
- **`create_all` را استفاده نکن.** فقط Alembic جدول می‌سازد.

---

## ۷. ساختار پوشه‌ها

```
beautyboss-ai/
├── app/
│   ├── core/          # تنظیمات مشترک (config.py)
│   ├── api/           # نفر اول
│   ├── auth/          # نفر اول
│   ├── database/      # مشترک: base.py, session.py, models.py
│   ├── chat/          # نفر اول
│   ├── integrations/  # نفر اول (spring_boot/)
│   ├── ai/            # نفر دوم (llm/, prompts/, orchestration/, memory/)
│   ├── rag/           # نفر اول
│   ├── products/      # نفر دوم
│   └── tools/         # مشترک
├── tests/
├── migrations/
├── docker-compose.yml
├── .env.example
└── pyproject.toml
```

همیشه از ریشه پروژه دستورها را اجرا کن (کنار `pyproject.toml`)، وگرنه `ModuleNotFoundError: app` می‌گیری.

---

## ۸. روش کار تیمی

- هر کار یک Issue کوچک در GitHub.
- هر ویژگی در یک branch جدا (`feature/...`) و ادغام با Pull Request.
- Review توسط نفر مقابل قبل از merge.
- تست‌ها قبل از ادغام اجرا شوند: `pytest`
- فایل `pyproject.toml` و `docker-compose.yml` را هماهنگ ویرایش کنید تا conflict نشود.
- هرگز commit نکن: `.env`، کلیدهای API، رمزها.

---

## ۹. مشکلات رایج

| مشکل | علت و راه‌حل |
|---|---|
| `ModuleNotFoundError: pydantic_settings` (یا پکیج دیگر) | env فعال نیست یا alembic از پایتون سیستم اجرا شده. `which alembic` را چک کن. مسیر باید داخل `env/bin/` باشد. یا بزن `python -m alembic ...` |
| `role "beautyboss" does not exist` | به PostgreSQL دیگری وصل می‌شوی (مثلاً نصب محلی روی ۵۴۳۲). پورت Docker را روی `5433` بگذار و در `DATABASE_URL` هم `5433` باشد. چک: `lsof -i :5432` |
| `password authentication failed` | رمز `POSTGRES_PASSWORD` با رمز `DATABASE_URL` فرق دارد. یکی کن و بعد `docker compose down -v && docker compose up -d db` |
| تغییر `.env` روی کاربر/رمز دیتابیس اثر نمی‌کند | این مقدارها فقط بار اول ساخت volume خوانده می‌شوند. `docker compose down -v` (**همه داده‌های دیتابیس محلی پاک می‌شود**) |
| `Target database is not up to date` | اول `alembic upgrade head` بزن، بعد `revision` |
| `Can't locate revision ...` | migration هم‌تیمی را pull نکرده‌ای: `git pull` |
| migration خالی ساخته شد (`pass`) | مدل‌ها در `migrations/env.py` ایمپورت نشده‌اند |
| متغیر `.env` اعمال نمی‌شود | متغیر محیطی شل روی `.env` غلبه می‌کند. `echo $DATABASE_URL` و در صورت وجود `unset DATABASE_URL` |
| دیتابیس هنوز آماده نیست | بعد از `up` صبر کن تا `docker compose ps` بگوید `healthy` |

---

## ۱۰. دستورهای مفید Docker

```bash
docker compose up -d db          # روشن
docker compose ps                # وضعیت
docker compose logs -f db        # لاگ
docker compose stop              # خاموش (داده می‌ماند)
docker compose down              # حذف کانتینر (داده می‌ماند)
docker compose down -v           # حذف کانتینر و داده‌ها ⚠️
docker compose exec db psql -U beautyboss -d beautyboss    # ورود به دیتابیس
```

---

## ۱۱. وضعیت فاز ۱

- [x] تنظیمات (`app/core/config.py`) و `.env`
- [x] PostgreSQL + pgvector در Docker
- [x] مدل‌های `Conversation` و `Message`
- [x] Alembic و migration اول
- [ ] کلاس LLM (`app/ai/llm/`) و `FakeLLMClient`
- [ ] کلاینت واقعی با timeout و retry
- [ ] تست‌ها و `scripts/llm_smoke.py`

---

## ۱۲. فاز ۴ — کاربر، امنیت و دیتابیس

> راهنمای اتصال به سایت اصلی (توکن، JWKS، CORS، پیشوند API): [`docs/INTEGRATION.md`](docs/INTEGRATION.md)

### هویت (JWT)
- `Authorization: Bearer <jwt>` ← کاربر لاگین‌شده؛ بدون هدر ← مهمان؛ توکن خراب/منقضی ← ۴۰۱.
- `user_id` فقط از claim توکن خوانده می‌شود (`JWT_USER_ID_CLAIM`، پیش‌فرض `sub`). هدر `X-User-Id` دیگر پذیرفته نمی‌شود.
- تنظیمات env: `JWT_ALGORITHM`, `JWT_SECRET` (HS*) یا `JWT_PUBLIC_KEY` (RS*), `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_ROLE_CLAIM`.

```bash
./env/bin/python scripts/make_test_token.py --user 42 --minutes 60
```

### مهمان در برابر کاربر
| | مهمان | لاگین‌شده |
|---|---|---|
| `POST /api/v1/chat` | ✅ ذخیره با شناسه نشست + `conversationId` | ✅ ذخیره + `conversationId` |
| `/api/v1/conversations...` | ✅ فقط چت‌های همان نشست مهمان | ✅ فقط چت‌های همان کاربر (چت دیگران ۴۰۴) |

شناسه نشست مهمان در مرورگر نگه داشته می‌شود تا گفتگوها بعد از بارگذاری دوباره قابل بازیابی باشند. درخواست جدید `/chat` یک گفتگو می‌سازد؛ برای ادامه، `conversationId` همان گفتگو را بفرستید. endpointهای `/conversations` نیز همین داده‌ها را نمایش می‌دهند.

### محدودیت‌ها
- `ANONYMOUS_RATE_PER_MINUTE=10`, `ANONYMOUS_RATE_PER_DAY=30`, `USER_RATE_PER_MINUTE=20`, `USER_RATE_PER_DAY=200` ← ۴۲۹ + `Retry-After`.
- `CHAT_MAX_MESSAGE_CHARS=2000` ← ۴۲۲.
- `DAILY_TOKEN_LIMIT` ← ۵۰۳ بدون فراخوانی LLM؛ مصرف در جدول `daily_usage` (migration `e1b7c4d9a2f3`).
- **مهم:** rate limit در حافظه است و فقط با **یک worker** درست کار می‌کند. برای چند worker فقط `app/limits.py` را با Redis عوض کن.
- `TRUST_PROXY_HEADERS=false` پیش‌فرض؛ فقط پشت reverse proxy مورد اعتماد `true` کن.

### اجرا
```bash
docker compose up -d db
./env/bin/python -m alembic upgrade head
./env/bin/python -m uvicorn app.main:app --reload
```

```bash
TOKEN=$(./env/bin/python scripts/make_test_token.py --user 42)
curl -s localhost:8000/api/v1/chat -H 'content-type: application/json' -d '{"content":"سلام"}'
curl -s localhost:8000/api/v1/chat -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"content":"سلام"}'
```
