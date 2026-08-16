# معماری فنی FreeLLM Studio

این فایل جزئیات فنی بخش Python پروژه را توضیح می‌دهد و عمداً از README اصلی جدا شده تا صفحه اول Repository کوتاه باقی بماند.

## 1. اجزای اصلی

### Desktop UI
رابط کاربری با `PySide6` پیاده‌سازی شده و بخش‌های زیر را در اختیار کاربر قرار می‌دهد:

- Overview
- Chat
- Local Models
- API Providers
- Gateway / Cline
- Diagnostics
- Logs
- Settings

عملیات شبکه‌ای و سنگین از UI جدا شده‌اند تا رابط کاربری در زمان Fetch Models، Test یا Chat قفل نشود.

## 2. Local Model Manager

مدل لوکال با `llama.cpp / llama-server` اجرا می‌شود.

پیش‌فرض پروژه:

```text
Repository: Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF
Quantization: Q4_K_M
Alias: local-qwen-lite
```

Runtime و فایل GGUF در Repository قرار نمی‌گیرند و فقط با درخواست کاربر دانلود می‌شوند.

مسیر Windows:

```text
%LOCALAPPDATA%\FreeLLMStudio\
```

ساختار داده‌های محلی:

```text
runtime/
models/
config/
logs/
downloads/
```

پورت پیش‌فرض Local Model:

```text
127.0.0.1:8080
```

برنامه قبل از Ready اعلام کردن مدل، endpointهای سرویس و inference را بررسی می‌کند.

## 3. Provider Abstraction

Providerهای داخلی:

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

برای Providerهای سازگار، مسیر استاندارد OpenAI استفاده می‌شود:

```text
/v1/models
/v1/chat/completions
```

در Test Connection فقط معتبر بودن کلید بررسی نمی‌شود؛ یک درخواست واقعی inference نیز اجرا می‌شود.

## 4. OpenAI-Compatible Bridge

FreeLLM Studio یک Bridge محلی ارائه می‌دهد:

```text
Base URL: http://127.0.0.1:8899/v1
Default API Key: freellm-studio-local
```

Bridge درخواست را به Provider فعال هدایت می‌کند.

معماری:

```text
Client
  |
  v
FreeLLMAPI
  |
  v
FreeLLM Studio Bridge
  |
  +--> Local llama.cpp
  |
  +--> Cloud Provider
```

مزیت این طراحی این است که FreeLLMAPI برای هر Provider مجدداً تنظیم نمی‌شود.

## 5. FreeLLMAPI / Cline

FreeLLMAPI در معماری حذف نشده است. نقش آن Gateway بین Cline و Bridge برنامه است.

نمونه مسیر:

```text
Cline
  -> FreeLLMAPI (localhost:3001/v1)
  -> FreeLLM Studio Bridge (localhost:8899/v1)
  -> Active Provider
```

## 6. Network / VPN

برای Providerهای Cloud، برنامه قابلیت استفاده از موارد زیر را دارد:

- Windows/System Proxy
- Environment Proxy
- Direct/TUN VPN
- Manual HTTP proxy
- Manual SOCKS proxy

ترافیک localhost برای Local Model و Bridge مستقیم باقی می‌ماند.

## 7. نگهداری API Key

API Keyها داخل Repository نوشته نمی‌شوند.

تنظیمات کاربر در مسیر Local AppData ذخیره می‌شوند. نسخه دانشگاهی برای اجرای پایدار روی Windows به PowerShell/.NET/DPAPI وابسته نیست. ذخیره کلید در این نسخه یک Credential Vault سازمانی محسوب نمی‌شود و هدف آن جلوگیری از قرار گرفتن Secret داخل Source Code و GitHub است.

## 8. Diagnostics

Diagnostics مواردی مانند این‌ها را بررسی می‌کند:

- Python
- requests
- llama.cpp runtime
- GGUF model
- Local API
- Bridge
- FreeLLMAPI endpoint
- Active Provider

## 9. Self-test

هسته بدون GUI:

```bash
python app.py --self-test
```

این تست به Model و API خارجی نیاز ندارد و برای بررسی سریع اجرای سورس در سیستم ارزیاب طراحی شده است.
