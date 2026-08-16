# زمینه و روند توسعه پروژه

## بخش اول — FreeLLMAPI + Cline

شروع پروژه بر پایه بررسی FreeLLMAPI بود:

- نصب و راه‌اندازی FreeLLMAPI
- تعریف API Providerهای مختلف
- بررسی محدودیت Providerها
- استفاده از fallback
- اتصال Unified API به Cline در VS Code
- بررسی Local/Cloud workflow

این بخش مبنای شناخت مسئله بود.

## بخش دوم — توسعه FreeLLM Studio با Python

برای این‌که خروجی پروژه فقط یک راهنمای نصب یا Repository مستنداتی نباشد، یک نرم‌افزار مستقل با Python توسعه داده شد.

هدف بخش دوم:

1. سورس پروژه واقعاً قابل اجرا باشد.
2. اجرای Local LLM به Docker وابسته نباشد.
3. مدیریت Providerها از یک UI انجام شود.
4. مدل و Runtime فقط در صورت نیاز دانلود شوند.
5. ارتباط با FreeLLMAPI از طریق یک Bridge استاندارد و ثابت انجام شود.
6. ارزیاب بتواند پروژه را با یک فایل `START.cmd` اجرا کند.

بنابراین بخش Python، **پیاده‌سازی اصلی و توسعه اختصاصی این Repository** محسوب می‌شود.

## سناریوی پیشنهادی برای ارزیابی

### سناریو A — بدون API Key

```text
START.cmd
-> Local Models
-> Install Runtime
-> Download Lite Model
-> Start Model
-> Chat
```

### سناریو B — Cloud Provider

```text
START.cmd
-> API Providers
-> انتخاب Groq/OpenRouter/...
-> API Key
-> Fetch Models
-> Test
-> Chat
```

### سناریو C — بررسی هسته

```text
TEST.cmd
```

در این حالت نیازی به دانلود Model یا داشتن API Key نیست.
