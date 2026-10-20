# فرانت‌اند دستیار هوشمند BeautyBoss (BeautyBoss AI)

رابط کاربری Angular برای بخش هوش مصنوعی سایت [beautyboss.ir](https://beautyboss.ir/) — مطابق «سند برنامه‌ریزی فنی و تقسیم مسئولیت‌ها» (نقشه راه دستیار هوشمند).

> این رابط **احراز هویت ندارد** و برای سوارشدن روی سایت اصلی طراحی شده است؛ هویت کاربر از میزبان (کوکی/توکن) به درخواست‌های HTTP ضمیمه می‌شود.

## قابلیت‌های فعلی

| بخش سند پروژه | پیاده‌سازی در رابط |
|---|---|
| فاز ۲ — سیستم چت و مدیریت مکالمات | صفحه «گفتگو»: ساخت گفتگو، فهرست و حذف، ارسال پیام، نشانگر تایپ، حالت خطا |
| فاز ۳ — جستجوی هوشمند آگهی (search_listings) | صفحه «جستجوی آگهی»: جستجوی زبان طبیعی + فیلتر دسته، کارت آگهی با قیمت/منطقه/لینک |
| فاز ۴ — RAG و مشاوره محصولات | رندر «منابع» پاسخ‌های تخصصی در حباب چت + سناریوی نمونه در حالت Mock |
| فاز ۳ — ثبت درخواست آگهی | **فعلاً از رابط حذف شده**؛ قرارداد سرویس و مدل‌ها برای افزودن مجدد باقی مانده‌اند |

## اجرا

پیش‌نیاز: Node.js نسخه `^20.19` یا `^22.12` یا بالاتر.

```bash
npm install
npm start        # اجرای توسعه روی http://localhost:4200
npm run build    # بیلد پروداکشن در dist/frontend
```

## اتصال به بکاند

فایل `src/app/core/environment.ts`:

```ts
export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8000/api', // سرویس FastAPI
  useMockApi: true,   // ← برای اتصال به بکاند واقعی false کنید
};
```

وقتی `useMockApi: true` باشد، سرویس‌های `MockChatApi` و `MockListingsApi` با داده نمونه جواب می‌دهند (آگهی‌های نمونه در رابط با برچسب «نمونه» مشخص‌اند). با `false`، پیاده‌سازی `HttpChatApi` و `HttpListingsApi` فعال می‌شود.

### قرارداد endpointهای مورد انتظار

| متد | مسیر | توضیح |
|---|---|---|
| GET | `/conversations` | فهرست مکالمات کاربر جاری |
| POST | `/conversations` | ساخت مکالمه (`{ title }`) |
| GET | `/conversations/{id}/messages` | تاریخچه پیام‌ها |
| POST | `/conversations/{id}/messages` | ارسال پیام (`{ content }`) → پیام پاسخ مدل |
| DELETE | `/conversations/{id}` | حذف مکالمه |
| GET | `/listings/categories` | معادل `get_listing_categories` |
| POST | `/listings/search` | معادل `search_listings` (`{ query, categoryId }`) |
| POST | `/listing-requests` | ثبت پیش‌نویس تأییدشده — فعلاً بدون رابط UI (فاز بعد) |

مدل‌های TypeScript این قرارداد در `src/app/core/models.ts` نگه‌داری می‌شوند؛ هر تغییر در API باید آن‌جا هم‌گام شود.

> طبق سند پروژه، در صورت پشتیبانی سرویس، ارسال پیام باید به **Streaming** ارتقا یابد — نقطه تعویض، متد `sendMessage` در `src/app/core/chat.service.ts` است.

## ساختار پروژه

```
src/app/
├── core/                  # مدل‌ها، تنظیمات و سرویس‌های چت/آگهی (Mock + HTTP)
├── shared/                # کامپوننت‌های مشترک (کارت آگهی)
├── features/
│   ├── chat/              # صفحه گفتگو (نوار مکالمات + رشته پیام + جعبه ارسال)
│   ├── search/            # جستجوی هوشمند آگهی
│   └── guide/             # راهنمای دستیار و مرزهای امنیتی
├── app.routes.ts          # مسیرها (Lazy Load)
└── app.config.ts          # providers (Router، HttpClient، ChatApi، ListingsApi)
```

## تم رنگی و فونت

- پالت از خود سایت beautyboss.ir استخراج شده و به‌صورت متغیر CSS در `src/styles.scss` تعریف شده است:
  بنفش اصلی `#7c3aed`، ارغوانی `#a855f7`، بنفش تیره `#4E1284` / `#2D1B40`، طلایی `#C29D59`، سطوح روشن `#FCFAFE` / `#f8f8f8` و خاکستری‌های slate.
- فونت: **Vazirmatn** (بسته npm، بدون وابستگی شبکه). سایت از «Vazir» استفاده می‌کند؛ Vazirmatn نسخه به‌روز همان خانواده است. اگر اصرار به فونت دقیق سایت دارید، فایل‌های Vazir را جایگزین `@font-face` کنید.
- کل اپ **RTL** و فارسی است (`<html lang="fa" dir="rtl">`).

## تغییرات رایج

| چه چیزی | کجا |
|---|---|
| رنگ‌ها | متغیرهای `--bb-*` در `src/styles.scss` |
| آدرس API | `src/app/core/environment.ts` |
| آگهی‌ها و دسته‌های نمونه | `src/app/core/listing.service.ts` |
| پاسخ‌های نمونه چت | `buildReply` در `src/app/core/chat.service.ts` |
| منوی ناوبری و هدر | `src/app/app.html` |
| افزودن مجدد «ثبت درخواست آگهی» | صفحه و مسیر را بازسازی کنید؛ قرارداد در `listing.service.ts` و `models.ts` آماده است |

> این ریپو فقط پیش‌نمایش رابط کاربری است؛ پاسخ‌های واقعی مدل و ثبت نهایی، پس از اتصال به سرویس‌های سند پروژه (FastAPI + Spring Boot) فعال می‌شوند.
