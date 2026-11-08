# اتصال سرویس AI به سایت اصلی

این سرویس یک **فیچر** از سایت اصلی (BeautyBoss) است: لاگین، ثبت‌نام، توکن و پروفایل دست سایت اصلی است و اینجا هیچ سیستم هویتی وجود ندارد. سرویس فقط توکن را **اعتبارسنجی** می‌کند.

## ۱. چیزی که سایت اصلی باید بدهد

| مورد | چطور |
|---|---|
| توکن کاربر | JWT در هدر `Authorization: Bearer <token>` |
| شناسه کاربر | در claim مشخص‌شده (`JWT_USER_ID_CLAIM`، پیش‌فرض `sub`) — باید **رشته** باشد |
| دامنه فرانت | با کاما در `CORS_ORIGINS` |
| کلید امضا | یکی از سه حالت پایین |

سه حالت اعتبارسنجی، به ترتیب اولویت:

1. `JWT_JWKS_URL` — آدرس JWKS (Keycloak: `https://<host>/realms/<realm>/protocol/openid-connect/certs`). بهترین گزینه؛ کلیدها هر ۵ دقیقه تازه می‌شوند و چرخش کلید مدیریت می‌شود.
2. `JWT_PUBLIC_KEY` + `JWT_ALGORITHM=RS256` — کلید عمومی ثابت (برای خط جدید `\n` بگذار).
3. `JWT_SECRET` + `JWT_ALGORITHM=HS256` — کلید مشترک.

اگر توکن `iss`/`aud` دارد و می‌خواهی چک شوند، `JWT_ISSUER` و `JWT_AUDIENCE` را ست کن؛ اگر خالی باشند چک نمی‌شوند.

### اگر شناسه کاربر عددی است

PyJWT طبق RFC، `sub` غیر رشته‌ای را رد می‌کند. در این حالت claim شناسه را عوض کن:

```env
JWT_USER_ID_CLAIM=userId
```

claim سفارشی عددی پشتیبانی می‌شود.

## ۲. رفتار درخواست‌ها

| درخواست | مهمان (بدون توکن) | کاربر (توکن معتبر) |
|---|---|---|
| `POST {API_PREFIX}/chat` | ۲۰۰، ذخیره با نشست مهمان و برگشت `conversationId` | ۲۰۰، ذخیره و برگشت `conversationId` |
| `GET/POST {API_PREFIX}/conversations...` | چت‌های همان نشست مهمان؛ نشست‌های دیگر ۴۰۴ | فقط چت‌های خودش؛ چت دیگران ۴۰۴ |
| `POST {API_PREFIX}/chat` با `conversationId` غیرمالک | ۴۰۴ | ۴۰۴ |

- توکن نامعتبر/منقضی → **۴۰۱** (`WWW-Authenticate: Bearer`)؛ به مهمان تبدیل نمی‌شود.
- `X-User-Id` یا هر شناسه‌ای در body/query **نادیده گرفته می‌شود**؛ هویت فقط از توکن.
- مهمان شناسه‌اش را با `X-Guest-Session-Id` (یا کوکی `bb_guest_session`) می‌فرستد تا نرخ‌محدودی و آگهی‌ها یکسان بمانند.
- خطاهای دیگر: ۴۲۲ (پیام خالی/بلندتر از `CHAT_MAX_MESSAGE_CHARS`)، ۴۲۹ (+`Retry-After`)، ۵۰۳ (بودجه روزانه تمام)، ۵۰۲ (خطای مدل).

## ۳. مسیر و CORS

- پیشوند پیش‌فرض `/api/v1` است؛ اگر سرویس را زیر مسیر دیگری mount می‌کنی: `API_PREFIX=/ai/api/v1`.
- اگر Spring به‌جای فرانت توکن را proxy می‌کند، CORS لازم نیست ولی `TRUST_PROXY_HEADERS=true` را فقط وقتی روشن کن که پروکسی خودت `X-Forwarded-For` را ست می‌کند.
- `CORS_ORIGINS` پیش‌فرض خالی است؛ بدون آن مرورگر پاسخ را دور می‌ریزد.

## ۴. فرانت (Angular)

- توکن در `localStorage` با کلید `environment.authTokenKey` (`bbai:access-token`) خوانده می‌شود — سایت اصلی بعد از لاگین همان‌جا بنویسد، یا `IdentityService.setToken(token)` را صدا بزند. خروج = `setToken(null)`.
- همه درخواست‌ها `Authorization: Bearer` می‌گیرند؛ برای مهمان `X-Guest-Session-Id`.
- گفتگوهای مهمان با `X-Guest-Session-Id` به همان نشست مرورگر محدود می‌شوند و در `POST /chat` و endpointهای `/conversations` ذخیره می‌شوند. برای ادامه چت با `POST /chat`، `conversationId` را ارسال کنید.
- `environment.apiBaseUrl` را روی آدرس واقعی سرویس بگذار.

## ۵. چک‌لیست اتصال

```bash
# ۱) تنظیمات سرویس
JWT_JWKS_URL=https://login.example/realms/beauty/protocol/openid-connect/certs
JWT_USER_ID_CLAIM=sub
CORS_ORIGINS=https://beautyboss.ir

# ۲) توکن دستی (فقط توسعه)
./env/bin/python scripts/make_test_token.py --user 42

# ۳) سه حالت
curl -i -X POST localhost:8000/api/v1/chat -H 'content-type: application/json' -d '{"content":"سلام"}'
curl -i -X POST localhost:8000/api/v1/chat -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"content":"سلام"}'
curl -i localhost:8000/api/v1/conversations -H "authorization: Bearer $TOKEN"
```

## ۶. چیزهایی که این سرویس **نمی‌کند**

- لاگین/ثبت‌نام/بازیابی رمز/ساخت توکن
- نگه‌داشتن پروفایل کاربر (فقط شناسه و نقش را از توکن می‌خواند)
- تصمیم دسترسی بر اساس نقش؛ `JWT_ROLE_CLAIM` فقط در `Identity.role` نگه داشته می‌شود و فعلاً جایی استفاده نمی‌شود
