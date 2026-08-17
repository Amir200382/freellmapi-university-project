# FreeLLM Studio — University Project

> **Python Desktop Manager for FreeLLMAPI, Local LLMs, Cloud API Providers & Cline**

این مخزن نسخه نهایی پروژه دانشگاهی **FreeLLMAPI** است.

پروژه در دو بخش انجام شده است:

1. **بررسی و راه‌اندازی FreeLLMAPI**، مدیریت ارائه‌دهنده‌ها (`Provider`)، مسیر جایگزین (`Fallback`) و اتصال به `Cline` در `Visual Studio Code`.
2. **طراحی و توسعه FreeLLM Studio با Python/PySide6** برای اجرای مدل محلی (`Local Model`)، مدیریت ارائه‌دهنده‌های آنلاین (`Online Provider`)، تست APIها، گفت‌وگوی داخلی (`Chat`)، پل سازگار با OpenAI (`OpenAI-Compatible Bridge`) و اتصال ساده‌تر به FreeLLMAPI.

> بخش دوم، یعنی **FreeLLM Studio**، توسعه اختصاصی این Repository است و سورس اجرایی آن در فایل `app.py` قرار دارد.

**درس:** پروژه نرم‌افزار  
**دانشگاه:** دانشگاه آزاد اسلامی واحد تهران مرکزی  
**ترم:** تابستان 4043  
**نسخه نرم‌افزار:** `1.2.1`

---

## دانلود و اجرای سریع

### دانلود سورس کامل

[⬇️ **دانلود نسخه کامل پروژه به‌صورت ZIP**](https://github.com/Amir200382/freellmapi-university-project/archive/refs/heads/main.zip)

یا از بالای صفحه GitHub:

```text
Code → Download ZIP
```

### اجرای پروژه

پس از دانلود:

1. فایل ZIP را Extract کنید.
2. وارد پوشه استخراج‌شده شوید.
3. فایل زیر را اجرا کنید:

```text
START.cmd
```

4. در اولین اجرا، برنامه به‌صورت خودکار:
   - یک محیط مجازی مستقل (`.venv`) می‌سازد.
   - وابستگی‌های Python را از `requirements.txt` نصب می‌کند.
   - برنامه اصلی را اجرا می‌کند.
5. در اجراهای بعدی، برنامه مستقیماً باز می‌شود.

### پیش‌نیاز

روی Windows فقط **Python 3.10 یا جدیدتر** نیاز است.

هنگام نصب Python بهتر است گزینه زیر فعال باشد:

```text
Add Python to PATH
```

---

# بخش اصلی پروژه — FreeLLM Studio

`FreeLLM Studio` یک نرم‌افزار Desktop است که با **Python و PySide6** توسعه داده شده و هدف آن یکپارچه‌سازی اجرای مدل محلی و استفاده از API ارائه‌دهنده‌های مختلف در یک رابط واحد است.

### امکانات اصلی

- رابط گرافیکی Desktop با `PySide6`
- اجرای مدل محلی با `llama.cpp`
- پشتیبانی از مدل‌های `GGUF`
- دانلود Runtime فقط در صورت نیاز
- دانلود مدل Lite فقط در صورت نیاز
- گفت‌وگوی داخلی (`Chat`)
- مدیریت ارائه‌دهنده‌های API (`API Provider`)
- دریافت فهرست مدل‌های در دسترس
- تست واقعی اتصال ارائه‌دهنده
- انتخاب ارائه‌دهنده فعال
- پل سازگار با OpenAI (`OpenAI-Compatible Bridge`)
- اتصال به FreeLLMAPI و `Cline`
- بخش عیب‌یابی و گزارش (`Diagnostics / Log`)
- تنظیمات شبکه، Proxy و VPN
- عدم ذخیره API Key داخل GitHub
- عدم نیاز به Docker برای اجرای خود FreeLLM Studio و مدل محلی

ارائه‌دهنده‌های موجود در نسخه فعلی:

```text
Local Model
Groq
OpenRouter
Gemini
OpenAI
DeepSeek
Together
Custom
```

---

# راهنمای ارزیابی و تست پروژه

برای بررسی پروژه دو روش اصلی وجود دارد.

> **روش دوم، یعنی استفاده از ارائه‌دهنده آنلاین (`Online Provider`)، روش پیشنهادی برای ارزیابی پروژه است.**
>
> استاد می‌تواند API Key آزمایشی که به‌صورت خصوصی برای ایشان ارسال می‌شود را داخل برنامه وارد کند و بدون نیاز به دانلود مدل محلی، بخش‌های اصلی نرم‌افزار شامل مدیریت ارائه‌دهنده، انتخاب مدل، تست اتصال و گفت‌وگو را بررسی کند.

---

## روش دوم — استفاده از ارائه‌دهنده آنلاین (`Online Provider`) با API Key — پیشنهادی

این روش برای ارزیابی سریع‌تر و ساده‌تر پروژه **پیشنهاد می‌شود**.

برای تست بخش ارائه‌دهنده‌های آنلاین، **یک API Key آزمایشی به‌صورت خصوصی در اختیار استاد قرار داده می‌شود**.

> API Key عمداً داخل GitHub قرار داده نشده است تا اطلاعات محرمانه در Repository عمومی منتشر نشود. استاد فقط کافی است کلید ارسال‌شده را در فیلد `API Key` برنامه وارد کند.

### مراحل اجرا

1. Repository را دانلود و Extract کنید.
2. فایل `START.cmd` را اجرا کنید.
3. از منوی سمت چپ وارد بخش زیر شوید:

```text
API Providers
```

4. ارائه‌دهنده (`Provider`) مربوط به API Key ارسال‌شده را انتخاب کنید.

برای مثال، اگر API Key مربوط به Groq باشد، گزینه زیر را انتخاب کنید:

```text
Groq
```

5. API Key ارسال‌شده را در فیلد `API Key` وارد کنید.
6. روی گزینه زیر کلیک کنید:

```text
Fetch models
```

7. یکی از مدل‌های نمایش‌داده‌شده را انتخاب کنید.
8. روی گزینه زیر کلیک کنید:

```text
Test
```

9. در صورت موفق بودن تست، ارائه‌دهنده آماده استفاده است.
10. در صورت نیاز، روی گزینه زیر کلیک کنید:

```text
Set active
```

11. وارد بخش `Chat` شوید.
12. ارائه‌دهنده مربوطه را انتخاب کرده و یک پیام آزمایشی ارسال کنید.

اگر پاسخ دریافت شود، ارتباط برنامه با ارائه‌دهنده آنلاین با موفقیت برقرار شده است.

### مسیر پیشنهادی برای استاد

```text
Download ZIP
    ↓
Extract
    ↓
START.cmd
    ↓
API Providers
    ↓
Select Provider
    ↓
Paste Private API Key
    ↓
Fetch models
    ↓
Select Model
    ↓
Test
    ↓
Chat
```

### مسیر ارتباط با ارائه‌دهنده آنلاین

```text
FreeLLM Studio
      │
      ▼
 Provider API
      │
      ├── Groq
      ├── OpenRouter
      ├── Gemini
      ├── OpenAI
      ├── DeepSeek
      ├── Together
      └── Custom
```

---

## روش اول — اجرای مدل محلی (`Local Model`) بدون API Key

این روش برای بررسی قابلیت اجرای مدل به‌صورت محلی است و به API Key خارجی نیاز ندارد.

پس از اجرای `START.cmd`:

1. از منوی سمت چپ وارد بخش زیر شوید:

```text
Local Models
```

2. روی گزینه زیر کلیک کنید:

```text
Install runtime
```

3. پس از نصب Runtime، روی گزینه زیر کلیک کنید:

```text
Download Lite model
```

4. پس از دانلود مدل، روی گزینه زیر کلیک کنید:

```text
Start model
```

5. صبر کنید وضعیت مدل به حالت آماده (`Ready`) برسد.
6. وارد بخش `Chat` شوید و یک پیام آزمایشی ارسال کنید.

### مدل پیش‌فرض Lite

```text
Qwen2.5-Coder-0.5B-Instruct
GGUF / Q4_K_M
```

Runtime و Model داخل Repository قرار داده نشده‌اند تا مخزن GitHub سبک باقی بماند.

این فایل‌ها هنگام نیاز دانلود شده و در Windows داخل مسیر زیر نگهداری می‌شوند:

```text
%LOCALAPPDATA%\FreeLLMStudio\
```

### مسیر ارتباط مدل محلی

```text
FreeLLM Studio
      │
      ▼
 llama.cpp
      │
      ▼
 GGUF Model
```

---

# تفاوت مدل محلی و ارائه‌دهنده آنلاین

| ویژگی | مدل محلی (`Local Model`) | ارائه‌دهنده آنلاین (`Online Provider`) |
|---|---|---|
| نیاز به API Key | خیر | بله |
| محل اجرای مدل | سیستم کاربر | سرور Provider |
| نیاز به اینترنت بعد از دانلود مدل | خیر | بله |
| نیاز به Runtime | بله | خیر |
| مدل GGUF | بله | خیر |
| دریافت فهرست مدل‌ها | خیر | بله |
| تست اتصال | سلامت و Inference محلی | API واقعی Provider |

---

# پل سازگار با OpenAI (`OpenAI-Compatible Bridge`)

FreeLLM Studio یک Bridge محلی سازگار با OpenAI ارائه می‌دهد.

آدرس پیش‌فرض:

```text
http://127.0.0.1:8899/v1
```

این Bridge درخواست‌ها را به ارائه‌دهنده فعال داخل برنامه هدایت می‌کند.

مزیت این معماری این است که ارائه‌دهنده و مدل فعال از داخل **FreeLLM Studio** قابل تغییر است و لایه‌های دیگر نیازی به تنظیم مجدد مداوم ندارند.

---

# اتصال FreeLLM Studio به FreeLLMAPI

در FreeLLMAPI می‌توان یک ارائه‌دهنده از نوع زیر تعریف کرد:

```text
Custom OpenAI-Compatible
```

اطلاعات Bridge در صفحه زیر داخل FreeLLM Studio نمایش داده می‌شود:

```text
Gateway / Cline
```

آدرس پیش‌فرض Base URL:

```text
http://127.0.0.1:8899/v1
```

پس از یک‌بار تنظیم FreeLLMAPI، تغییر ارائه‌دهنده یا مدل از داخل FreeLLM Studio قابل انجام است.

---

# اتصال به Cline

در بخش اول پروژه، `Cline` در `Visual Studio Code` به API یکپارچه FreeLLMAPI متصل می‌شود.

ساختار کلی:

```text
Cline
  │
  ▼
FreeLLMAPI
  │
  ▼
FreeLLM Studio Bridge
  │
  ├── Local Model
  └── Online Provider
```

در تنظیمات Cline، نوع ارائه‌دهنده باید روی حالت سازگار با OpenAI قرار بگیرد:

```text
OpenAI Compatible
```

---

# تست سریع سورس بدون دانلود مدل و بدون API Key

اگر هدف فقط بررسی اجرای سورس و هسته برنامه باشد، فایل زیر را اجرا کنید:

```text
TEST.cmd
```

یا از CMD / PowerShell:

```text
python app.py --self-test
```

Self-test برای بررسی سریع بخش‌های اصلی هسته و Bridge طراحی شده و برای اجرای آن به API Key یا دانلود مدل خارجی نیاز نیست.

---

# ساختار Repository

```text
freellmapi-university-project/
├── app.py
├── START.cmd
├── TEST.cmd
├── requirements.txt
├── VERSION
├── .gitignore
├── README.md
└── docs/
    ├── ARCHITECTURE.md
    ├── PROJECT_CONTEXT.md
    └── CHANGELOG.md
```

### فایل‌های اصلی

| فایل | توضیح |
|---|---|
| `app.py` | سورس اصلی FreeLLM Studio |
| `START.cmd` | ساخت محیط مجازی، نصب وابستگی‌ها و اجرای نرم‌افزار |
| `TEST.cmd` | اجرای Self-test |
| `requirements.txt` | وابستگی‌های Python |
| `docs/ARCHITECTURE.md` | معماری فنی پروژه |
| `docs/PROJECT_CONTEXT.md` | ارتباط بخش FreeLLMAPI با توسعه Python |
| `docs/CHANGELOG.md` | تغییرات نسخه‌ها |

---

# امنیت

اطلاعات زیر نباید داخل Repository عمومی Commit شوند:

```text
API Keys
.env
Tokens
Passwords
Runtime binaries
GGUF models
Logs containing secrets
```

به همین دلیل API Key مربوط به تست Provider به‌صورت خصوصی ارسال می‌شود و داخل GitHub قرار نمی‌گیرد.

همچنین فایل‌های Runtime، Model و Virtual Environment توسط `.gitignore` از Repository خارج نگه داشته شده‌اند.

---

# بخش اول پروژه — FreeLLMAPI

شروع پروژه بر پایه بررسی و اجرای FreeLLMAPI بود.

موارد بررسی‌شده:

- نصب و راه‌اندازی FreeLLMAPI
- مدیریت ارائه‌دهنده‌ها (`Provider`)
- دریافت API Key از ارائه‌دهنده‌های مختلف
- بررسی مدل‌ها
- مسیر جایگزین بین مدل‌ها (`Fallback`)
- بخش آزمایش (`Playground`)
- API یکپارچه (`Unified API`)
- اتصال به `Cline`
- استفاده از API سازگار با OpenAI
- بررسی اجرای مدل‌های محلی و سرویس‌های ابری

این مرحله مبنای طراحی بخش دوم پروژه، یعنی **FreeLLM Studio**، شد.

---

# چرا بخش Python توسعه داده شد؟

نسخه اولیه پروژه بیشتر بر نصب، تنظیم و بررسی FreeLLMAPI تمرکز داشت.

برای این‌که خروجی نهایی پروژه فقط یک Repository مستنداتی نباشد و **سورس اجرایی قابل ارزیابی** نیز در اختیار استاد قرار بگیرد، FreeLLM Studio با Python توسعه داده شد.

اهداف این توسعه:

1. ارائه سورس اجرایی مستقل
2. ساده‌تر کردن اجرای پروژه
3. کاهش مراحل نصب پراکنده
4. اجرای Local LLM بدون Docker
5. مدیریت ارائه‌دهنده‌ها از یک رابط واحد
6. تست APIها و مدل‌ها
7. ایجاد Bridge سازگار با OpenAI
8. امکان اتصال به FreeLLMAPI و `Cline`
9. امکان اجرای پروژه توسط استاد تنها با `START.cmd`

---

# ویدیوی پروژه

ویدیوی اجرای پروژه شامل مراحل FreeLLMAPI، Cline و بخش Python تهیه شده است.

لینک ویدیوی ارائه قبلی:

[▶️ مشاهده ویدیوی پروژه](https://drive.google.com/file/d/1yDVhFRk7pRmxaFJIKEIIzoiOmvJRG-IQ/preview)

---

# نکته مهم برای ارزیابی

این Repository صرفاً راهنمای نصب FreeLLMAPI نیست.

**بخش توسعه‌یافته پروژه، FreeLLM Studio، به‌صورت کامل در فایل `app.py` قرار دارد و قابل اجرا است.**

ساده‌ترین روش بررسی:

```text
Download ZIP
     ↓
Extract
     ↓
START.cmd
     ↓
FreeLLM Studio
```

برای ارزیابی، **روش دوم یعنی استفاده از ارائه‌دهنده آنلاین (`Online Provider`) پیشنهاد می‌شود**.

استاد می‌تواند API Key آزمایشی ارسال‌شده به‌صورت خصوصی را در برنامه وارد کند و مسیر زیر را بررسی کند:

```text
API Providers → Select Provider → Paste Private API Key → Fetch models → Select Model → Test → Chat
```

در صورت تمایل، روش Local نیز بدون API Key قابل بررسی است:

```text
Local Models → Install runtime → Download Lite model → Start model → Chat
```

---

# مستندات بیشتر

برای جزئیات فنی:

- [`docs/ARCHITECTURE.md`](https://github.com/Amir200382/freellmapi-university-project/blob/main/docs/ARCHITECTURE.md)
- [`docs/PROJECT_CONTEXT.md`](https://github.com/Amir200382/freellmapi-university-project/blob/main/docs/PROJECT_CONTEXT.md)
- [`docs/CHANGELOG.md`](https://github.com/Amir200382/freellmapi-university-project/blob/main/docs/CHANGELOG.md)

---

# اعتبار و پروژه اصلی FreeLLMAPI

FreeLLMAPI یک پروژه متن‌باز مستقل است و حقوق سورس اصلی آن متعلق به نویسندگان و مشارکت‌کنندگان همان پروژه است.

در این Repository:

- بررسی و راه‌اندازی FreeLLMAPI بخشی از پروژه دانشگاهی بوده است.
- **FreeLLM Studio و سورس Python موجود در `app.py` بخش توسعه اختصاصی این پروژه است.**

مخزن اصلی FreeLLMAPI:

https://github.com/tashfeenahmed/freellmapi
