<h1 dir="rtl" align="right">راه‌اندازی <code>FreeLLMAPI</code> روی ویندوز و اتصال به <code>Cline</code></h1>

<h2 dir="rtl" align="right">🎥 ویدیوی کامل اجرای پروژه</h2>

<p dir="rtl" align="right">
<a href="https://drive.google.com/file/d/1yDVhFRk7pRmxaFJIKEIIzoiOmvJRG-IQ/preview">
<strong>▶️ برای مشاهده مستقیم ویدیوی کامل پروژه کلیک کنید</strong>
</a>
</p>

<blockquote dir="rtl">
در این ویدئو، مراحل نصب، تنظیم فایل <code>.env</code>، افزودن کلید رابط برنامه‌نویسی، آزمایش سامانه و اتصال آن به <code>Cline</code> در محیط <code>Visual Studio Code</code> نمایش داده شده است.
</blockquote>

<p dir="rtl" align="right">
نسخه قابل دانلود ویدئو نیز در
<a href="https://github.com/Amir200382/freellmapi-university-project/releases/tag/v1.0.0">
بخش انتشار نسخهٔ ۱٫۰٫۰
</a>
قرار دارد.
</p>

<hr>

<h2 dir="rtl" align="right">معرفی پروژه</h2>

<p dir="rtl" align="right">
این مخزن برای ارائهٔ دانشگاهیِ نصب، راه‌اندازی، پیکربندی، آزمایش و مستندسازی
<code>FreeLLMAPI</code>
روی سیستم‌عامل ویندوز ایجاد شده است.
</p>

<p dir="rtl" align="right">
در این پروژه، سامانهٔ
<code>FreeLLMAPI</code>
به‌عنوان یک درگاه محلی و سازگار با رابط
<code>OpenAI</code>
اجرا می‌شود. سپس افزونهٔ
<code>Cline</code>
در محیط
<code>Visual Studio Code</code>
از طریق یک نشانی پایه و یک کلید یکپارچه به آن متصل می‌شود.
</p>

<blockquote dir="rtl">
کد اصلی این پروژه متعلق به نویسندگان و مشارکت‌کنندگان مخزن رسمی
<code>FreeLLMAPI</code>
است. فعالیت انجام‌شده در این مخزن شامل نصب، پیکربندی، آزمایش، مستندسازی و تهیهٔ ویدیوی آموزشی است.
</blockquote>

<h2 dir="rtl" align="right">هدف پروژه</h2>

<ul dir="rtl" align="right">
  <li>دریافت و اجرای پروژه روی ویندوز</li>
  <li>ساخت و تنظیم فایل <code>.env</code></li>
  <li>تولید کلید رمزنگاری امن</li>
  <li>افزودن کلیدهای ارائه‌دهندگان مدل‌های هوش مصنوعی</li>
  <li>ساخت کلید یکپارچه برای برنامه‌های مصرف‌کننده</li>
  <li>تنظیم مدل‌ها و مسیر جایگزین</li>
  <li>آزمایش درخواست‌ها در محیط داخلی پروژه</li>
  <li>بررسی گزارش درخواست‌ها و خطاها</li>
  <li>اتصال پروژه به افزونهٔ <code>Cline</code></li>
  <li>تهیهٔ مستندات و ویدیوی آموزشی</li>
</ul>

<h2 dir="rtl" align="right"><code>FreeLLMAPI</code> چیست؟</h2>

<p dir="rtl" align="right">
<code>FreeLLMAPI</code>
یک ابزار متن‌باز برای مدیریت چند ارائه‌دهنده و چند مدل هوش مصنوعی از طریق یک رابط یکپارچه و سازگار با
<code>OpenAI API</code>
است.
</p>

<p dir="rtl" align="right">
این ابزار خودش مدل هوش مصنوعی نیست. نقش آن شبیه یک درگاه، مسیریاب یا واسط است؛ یعنی درخواست را از برنامه‌ای مانند
<code>Cline</code>
دریافت می‌کند و آن را بر اساس تنظیمات موجود به یکی از مدل‌ها یا ارائه‌دهندگان فعال می‌فرستد.
</p>

<h2 dir="rtl" align="right">ساختار کلی ارتباط</h2>

```text
Cline یا برنامهٔ مصرف‌کننده
            |
            | OpenAI-Compatible Request
            v
       FreeLLMAPI
            |
            | Keys, Models, Fallback
            v
 ارائه‌دهنده یا مدل انتخاب‌شده
            |
            v
      پاسخ نهایی به Cline
```

<p dir="rtl" align="right">
برنامهٔ مصرف‌کننده معمولاً فقط به سه مقدار نیاز دارد:
</p>

<ul dir="rtl" align="right">
  <li>نشانی پایه</li>
  <li>کلید یکپارچه</li>
  <li>شناسهٔ مدل</li>
</ul>

<h2 dir="rtl" align="right">قابلیت‌های اصلی</h2>

<ul dir="rtl" align="right">
  <li>ارائهٔ رابط سازگار با <code>OpenAI</code></li>
  <li>مدیریت چند ارائه‌دهنده از یک داشبورد</li>
  <li>نگهداری متمرکز کلیدهای رابط برنامه‌نویسی</li>
  <li>ساخت کلید یکپارچه برای برنامه‌های دیگر</li>
  <li>تعریف ترتیب جایگزینی مدل‌ها</li>
  <li>بررسی سلامت کلیدها و ارائه‌دهندگان</li>
  <li>آزمایش درخواست‌ها در محیط داخلی پروژه</li>
  <li>مشاهدهٔ آمار، خطاها و زمان پاسخ</li>
  <li>اتصال به ابزارهایی مانند <code>Cline</code></li>
</ul>

<hr>

<h2 dir="rtl" align="right">پیش‌نیازها</h2>

<ul dir="rtl" align="right">
  <li>ویندوز ۱۰ یا ویندوز ۱۱</li>
  <li><code>Git</code></li>
  <li><code>Node.js</code> نسخهٔ ۲۰ یا جدیدتر</li>
  <li><code>npm</code></li>
  <li><code>Docker Desktop</code> برای روش مبتنی بر کانتینر</li>
  <li><code>Visual Studio Code</code></li>
  <li>افزونهٔ <code>Cline</code></li>
  <li>کلید معتبر حداقل یک ارائه‌دهنده</li>
</ul>

<p dir="rtl" align="right">بررسی نصب ابزارها:</p>

```powershell
git --version
node --version
npm --version
docker --version
```

<hr>

<h2 dir="rtl" align="right">مرحلهٔ ۱: ساخت پوشهٔ پروژه</h2>

```powershell
New-Item -ItemType Directory -Force "$HOME\Projects" | Out-Null
Set-Location "$HOME\Projects"
```

<h2 dir="rtl" align="right">مرحلهٔ ۲: دریافت سورس پروژه</h2>

```powershell
git clone https://github.com/tashfeenahmed/freellmapi.git
cd freellmapi
```

<p dir="rtl" align="right">
مسیر پروژه معمولاً به شکل زیر خواهد بود:
</p>

```text
C:\Users\USERNAME\Projects\freellmapi
```

<h2 dir="rtl" align="right">مرحلهٔ ۳: ساخت فایل تنظیمات محیطی</h2>

```powershell
Copy-Item .env.example .env
```

<p dir="rtl" align="right">
فایل
<code>.env</code>
حاوی تنظیمات حساس پروژه است و نباید داخل مخزن عمومی قرار بگیرد.
</p>

<h2 dir="rtl" align="right">مرحلهٔ ۴: تولید کلید رمزنگاری امن</h2>

```powershell
$encryptionKey = node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

<p dir="rtl" align="right">برای مشاهدهٔ مقدار تولیدشده:</p>

```powershell
$encryptionKey
```

<blockquote dir="rtl">
این مقدار محرمانه است. آن را در مخزن عمومی، تصویر یا ویدئوی قابل انتشار نمایش ندهید.
</blockquote>

<h2 dir="rtl" align="right">مرحلهٔ ۵: تنظیم فایل <code>.env</code></h2>

```powershell
@"
ENCRYPTION_KEY=$encryptionKey
PORT=3001
"@ | Out-File -FilePath .env -Encoding utf8
```

<p dir="rtl" align="right">نمونهٔ محتوای فایل:</p>

```env
ENCRYPTION_KEY=YOUR_SECURE_RANDOM_KEY
PORT=3001
```

<blockquote dir="rtl">
عبارت
<code>YOUR_SECURE_RANDOM_KEY</code>
فقط نمونه است و باید با کلید واقعی تولیدشده جایگزین شود.
</blockquote>

<hr>

<h2 dir="rtl" align="right">روش اول: اجرای پروژه با <code>Docker</code></h2>

<p dir="rtl" align="right">
این روش برای اجرای پایدار و ساده‌تر پروژه پیشنهاد می‌شود.
</p>

<h3 dir="rtl" align="right">اجرای کانتینرها</h3>

```powershell
docker compose up -d
```

<h3 dir="rtl" align="right">بررسی وضعیت اجرا</h3>

```powershell
docker compose ps
```

<p dir="rtl" align="right">
در صورت اجرای موفق، وضعیت کانتینر باید
<code>running</code>
یا
<code>healthy</code>
باشد و پورت
<code>3001</code>
نمایش داده شود.
</p>

<h3 dir="rtl" align="right">مشاهدهٔ گزارش اجرا</h3>

```powershell
docker compose logs -f
```

<p dir="rtl" align="right">
برای خروج از حالت نمایش گزارش‌ها، کلیدهای زیر را فشار دهید:
</p>

```text
Ctrl + C
```

<h3 dir="rtl" align="right">توقف پروژه</h3>

```powershell
docker compose down
```

<h3 dir="rtl" align="right">اجرای دوباره</h3>

```powershell
docker compose up -d
```

<h3 dir="rtl" align="right">راه‌اندازی مجدد</h3>

```powershell
docker compose restart
```

<hr>

<h2 dir="rtl" align="right">روش دوم: اجرای محلی با <code>npm</code></h2>

<p dir="rtl" align="right">
این روش بیشتر برای توسعه، بررسی سورس یا اجرای مستقیم پروژه مناسب است.
</p>

<h3 dir="rtl" align="right">نصب وابستگی‌ها</h3>

```powershell
npm install
```

<h3 dir="rtl" align="right">اجرای پروژه</h3>

```powershell
npm run dev
```

<p dir="rtl" align="right">
آدرس دقیق داشبورد و رابط برنامه‌نویسی در خروجی ترمینال نمایش داده می‌شود.
</p>

<p dir="rtl" align="right">
برای توقف اجرای محلی، در همان پنجرهٔ ترمینال کلیدهای زیر را فشار دهید:
</p>

```text
Ctrl + C
```

<hr>

<h2 dir="rtl" align="right">نشانی‌های اصلی پروژه</h2>

<h3 dir="rtl" align="right">داشبورد</h3>

```text
http://localhost:3001
```

<h3 dir="rtl" align="right">نشانی پایهٔ سازگار با <code>OpenAI</code></h3>

```text
http://localhost:3001/v1
```

<h3 dir="rtl" align="right">مسیر گفت‌وگو</h3>

```text
http://localhost:3001/v1/chat/completions
```

<h3 dir="rtl" align="right">مسیر مدل‌ها</h3>

```text
http://localhost:3001/v1/models
```

<hr>

<h2 dir="rtl" align="right">تنظیم کلیدهای ارائه‌دهندگان</h2>

<p dir="rtl" align="right">
بعد از ورود به داشبورد، وارد بخش
<code>Keys</code>
شوید و مراحل زیر را انجام دهید:
</p>

<ol dir="rtl" align="right">
  <li>ارائه‌دهندهٔ موردنظر را انتخاب کنید.</li>
  <li>کلید رسمی همان سرویس را وارد کنید.</li>
  <li>در صورت نیاز، یک عنوان برای کلید بنویسید.</li>
  <li>کلید را ذخیره کنید.</li>
  <li>بررسی سلامت یا آزمون اتصال را اجرا کنید.</li>
  <li>از معتبر بودن کلید و دسترسی به مدل مطمئن شوید.</li>
</ol>

<blockquote dir="rtl">
کلید واقعی ارائه‌دهندگان نباید داخل
<code>GitHub</code>
یا مستندات عمومی قرار بگیرد.
</blockquote>

<h2 dir="rtl" align="right">نمونهٔ ارائه‌دهندگان قابل اتصال</h2>

<ul dir="rtl" align="right">
  <li><code>Google AI Studio</code></li>
  <li><code>GitHub Models</code></li>
  <li><code>OpenRouter</code></li>
  <li><code>Groq</code></li>
  <li><code>Mistral</code></li>
  <li><code>Cohere</code></li>
  <li><code>Hugging Face</code></li>
  <li><code>Cloudflare</code></li>
  <li><code>NVIDIA NIM</code></li>
  <li><code>Ollama</code></li>
  <li>رابط‌های سفارشی سازگار با <code>OpenAI</code></li>
</ul>

<blockquote dir="rtl">
فهرست سرویس‌ها، مدل‌ها و سهمیه‌های رایگان ممکن است در نسخه‌های مختلف تغییر کند.
</blockquote>

<hr>

<h2 dir="rtl" align="right">ساخت کلید یکپارچه</h2>

<p dir="rtl" align="right">
در داشبورد، یک کلید یکپارچه برای اتصال برنامه‌هایی مانند
<code>Cline</code>
ایجاد کنید.
</p>

<p dir="rtl" align="right">نمونهٔ نمایشی:</p>

```text
freellmapi-xxxxxxxxxxxxxxxx
```

<blockquote dir="rtl">
این مقدار فقط نمونه است. کلید واقعی را در مخزن عمومی منتشر نکنید.
</blockquote>

<hr>

<h2 dir="rtl" align="right">تنظیم مسیر جایگزین</h2>

<p dir="rtl" align="right">
در بخش
<code>Fallback</code>
می‌توان ترتیب مدل‌ها را مشخص کرد. درخواست ابتدا به مدل اول فرستاده می‌شود و در صورت بروز خطا، مدل بعدی آزمایش خواهد شد.
</p>

<p dir="rtl" align="right">نمونهٔ ترتیب:</p>

```text
1. GitHub Models
2. OpenRouter
3. Groq
4. Ollama
```

<p dir="rtl" align="right">
قابلیت‌های این بخش معمولاً شامل موارد زیر است:
</p>

<ul dir="rtl" align="right">
  <li>تغییر ترتیب مدل‌ها</li>
  <li>فعال یا غیرفعال‌کردن مدل‌ها</li>
  <li>انتخاب اولویت سرعت یا کیفیت</li>
  <li>تعریف مسیر جایگزین هنگام خطا</li>
  <li>مشاهدهٔ وضعیت ارائه‌دهندهٔ هر مدل</li>
</ul>

<hr>

<h2 dir="rtl" align="right">آزمایش در محیط داخلی پروژه</h2>

<p dir="rtl" align="right">
برای آزمایش مستقیم، وارد بخش
<code>Playground</code>
شوید:
</p>

<ol dir="rtl" align="right">
  <li>مدل را روی حالت خودکار قرار دهید.</li>
  <li>یک پیام آزمایشی وارد کنید.</li>
  <li>درخواست را ارسال کنید.</li>
  <li>پاسخ و نام مدل پاسخ‌دهنده را بررسی کنید.</li>
</ol>

<p dir="rtl" align="right">نمونهٔ پیام:</p>

```text
سلام، خودت را در یک جمله معرفی کن.
```

<hr>

<h2 dir="rtl" align="right">بررسی گزارش‌ها و آمار</h2>

<p dir="rtl" align="right">
در بخش
<code>Analytics</code>
می‌توان اطلاعاتی مانند موارد زیر را مشاهده کرد:
</p>

<ul dir="rtl" align="right">
  <li>تعداد درخواست‌ها</li>
  <li>تعداد پاسخ‌های موفق</li>
  <li>تعداد خطاها</li>
  <li>مدل پاسخ‌دهنده</li>
  <li>ارائه‌دهندهٔ استفاده‌شده</li>
  <li>زمان پاسخ</li>
  <li>تعداد توکن‌ها</li>
  <li>عملکرد مسیر جایگزین</li>
</ul>

<hr>

<h2 dir="rtl" align="right">اتصال به <code>Cline</code></h2>

<h3 dir="rtl" align="right">۱. نصب افزونه</h3>

<p dir="rtl" align="right">
در
<code>Visual Studio Code</code>
وارد بخش افزونه‌ها شوید و افزونهٔ
<code>Cline</code>
را نصب کنید.
</p>

<h3 dir="rtl" align="right">۲. انتخاب نوع ارائه‌دهنده</h3>

<p dir="rtl" align="right">
در تنظیمات
<code>Cline</code>
نوع اتصال را روی حالت سازگار با
<code>OpenAI</code>
قرار دهید.
</p>

```text
OpenAI Compatible
```

<h3 dir="rtl" align="right">۳. واردکردن نشانی پایه</h3>

```text
http://localhost:3001/v1
```

<h3 dir="rtl" align="right">۴. واردکردن کلید</h3>

<p dir="rtl" align="right">
کلید یکپارچه‌ای را که داخل داشبورد ساخته‌اید وارد کنید.
</p>

```text
freellmapi-xxxxxxxxxxxxxxxx
```

<h3 dir="rtl" align="right">۵. واردکردن شناسهٔ مدل</h3>

<p dir="rtl" align="right">
شناسهٔ مدل باید دقیقاً با مدل فعال در داشبورد مطابقت داشته باشد.
</p>

```text
auto
```

<p dir="rtl" align="right">یا:</p>

```text
provider/model-name
```

<h3 dir="rtl" align="right">۶. آزمایش اتصال</h3>

<p dir="rtl" align="right">
در پنل
<code>Cline</code>
یک درخواست ساده ارسال کنید:
</p>

```text
یک فایل متنی با نام test.txt ایجاد کن و داخل آن عبارت Hello FreeLLMAPI را بنویس.
```

<p dir="rtl" align="right">
در صورت دریافت پاسخ و ثبت درخواست در بخش گزارش‌ها، اتصال با موفقیت انجام شده است.
</p>

<hr>

<h2 dir="rtl" align="right">آزمایش مستقیم رابط برنامه‌نویسی با <code>PowerShell</code></h2>

<h3 dir="rtl" align="right">تعریف متغیرها</h3>

```powershell
$BaseUrl = "http://localhost:3001/v1"
$ApiKey = "YOUR_UNIFIED_API_KEY"
$Model = "YOUR_MODEL_ID"
```

<h3 dir="rtl" align="right">ساخت سربرگ درخواست</h3>

```powershell
$Headers = @{
    "Authorization" = "Bearer $ApiKey"
    "Content-Type"  = "application/json"
}
```

<h3 dir="rtl" align="right">ساخت بدنهٔ درخواست</h3>

```powershell
$Body = @{
    model = $Model
    messages = @(
        @{
            role = "user"
            content = "سلام، این یک آزمایش FreeLLMAPI است."
        }
    )
} | ConvertTo-Json -Depth 10
```

<h3 dir="rtl" align="right">ارسال درخواست</h3>

```powershell
Invoke-RestMethod `
    -Uri "$BaseUrl/chat/completions" `
    -Method Post `
    -Headers $Headers `
    -Body $Body
```

<blockquote dir="rtl">
مقادیر
<code>YOUR_UNIFIED_API_KEY</code>
و
<code>YOUR_MODEL_ID</code>
باید با اطلاعات واقعی سیستم جایگزین شوند، اما نباید در مخزن عمومی ذخیره شوند.
</blockquote>

<hr>

<h2 dir="rtl" align="right">به‌روزرسانی پروژه</h2>

```powershell
cd "$HOME\Projects\freellmapi"
git pull
npm install
```

<p dir="rtl" align="right">
پس از دریافت تغییرات، پروژه را با یکی از روش‌های اجرای
<code>Docker</code>
یا
<code>npm</code>
دوباره راه‌اندازی کنید.
</p>

<hr>

<h2 dir="rtl" align="right">رفع خطاهای متداول</h2>

<h3 dir="rtl" align="right">شناسایی‌نشدن <code>Git</code></h3>

```text
git is not recognized
```

<p dir="rtl" align="right">
برنامهٔ
<code>Git</code>
را نصب کنید، ترمینال را ببندید و دوباره باز کنید.
</p>

```powershell
git --version
```

<h3 dir="rtl" align="right">شناسایی‌نشدن <code>Node.js</code></h3>

```text
node is not recognized
```

<p dir="rtl" align="right">
نسخهٔ مناسب
<code>Node.js</code>
را نصب کرده و ترمینال را دوباره باز کنید.
</p>

```powershell
node --version
```

<h3 dir="rtl" align="right">خطای نصب وابستگی‌ها</h3>

```powershell
npm cache verify
npm install
```

<h3 dir="rtl" align="right">اشغال‌بودن پورت ۳۰۰۱</h3>

```powershell
Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue
```

<p dir="rtl" align="right">یا:</p>

```powershell
netstat -ano | findstr :3001
```

<p dir="rtl" align="right">
در صورت نیاز، پورت را در فایل
<code>.env</code>
تغییر دهید:
</p>

```env
PORT=3002
```

<p dir="rtl" align="right">
بعد از تغییر پورت، نشانی پایه نیز باید اصلاح شود:
</p>

```text
http://localhost:3002/v1
```

<h3 dir="rtl" align="right">بازنشدن داشبورد</h3>

<ul dir="rtl" align="right">
  <li>فعال‌بودن پروژه را بررسی کنید.</li>
  <li>خروجی ترمینال را برای خطا بررسی کنید.</li>
  <li>پورت صحیح را وارد کنید.</li>
  <li>وضعیت دیوارهٔ آتش را بررسی کنید.</li>
  <li>در روش کانتینری، وضعیت کانتینرها را بررسی کنید.</li>
</ul>

```powershell
docker compose ps
```

<h3 dir="rtl" align="right">خطای کلید ارائه‌دهنده</h3>

<ul dir="rtl" align="right">
  <li>صحیح‌بودن کلید را بررسی کنید.</li>
  <li>انقضای کلید را بررسی کنید.</li>
  <li>دسترسی مدل را بررسی کنید.</li>
  <li>محدودیت منطقه‌ای یا سهمیه را بررسی کنید.</li>
  <li>آزمون سلامت را دوباره اجرا کنید.</li>
</ul>

<h3 dir="rtl" align="right">خطای اتصال <code>Cline</code></h3>

<ul dir="rtl" align="right">
  <li>فعال‌بودن <code>FreeLLMAPI</code> را بررسی کنید.</li>
  <li>نشانی پایه را کنترل کنید.</li>
  <li>کلید یکپارچه را کنترل کنید.</li>
  <li>شناسهٔ مدل را بررسی کنید.</li>
  <li>فعال‌بودن حداقل یک مدل را بررسی کنید.</li>
  <li>وضعیت مسیر جایگزین را کنترل کنید.</li>
</ul>

<hr>

<h2 dir="rtl" align="right">نکات امنیتی</h2>

<p dir="rtl" align="right">
اطلاعات زیر نباید در مخزن عمومی قرار بگیرند:
</p>

<ul dir="rtl" align="right">
  <li>فایل <code>.env</code></li>
  <li>مقدار <code>ENCRYPTION_KEY</code></li>
  <li>کلید ارائه‌دهندگان</li>
  <li>کلید یکپارچه</li>
  <li>رمزهای عبور</li>
  <li>توکن شخصی گیت‌هاب</li>
  <li>فایل‌های پایگاه داده</li>
  <li>تصاویر یا ویدئوهای حاوی اطلاعات محرمانه</li>
</ul>

<h3 dir="rtl" align="right">نمونهٔ فایل <code>.gitignore</code></h3>

```gitignore
.env
.env.*
!.env.example

node_modules/
dist/
build/

*.db
*.sqlite
*.sqlite3
*.log

data/
logs/
backups/

*.key
*.pem

.vscode/settings.json
.idea/

Thumbs.db
.DS_Store
```

<hr>

<h2 dir="rtl" align="right">محدودیت‌های پروژه</h2>

<ul dir="rtl" align="right">
  <li>سهمیه‌های رایگان ارائه‌دهندگان دائمی و نامحدود نیستند.</li>
  <li>مدل‌های رایگان ممکن است حذف یا محدود شوند.</li>
  <li>برخی سرویس‌ها ممکن است در همهٔ مناطق در دسترس نباشند.</li>
  <li>مسیر جایگزین، کیفیت یکسان پاسخ‌ها را تضمین نمی‌کند.</li>
  <li>هر تلاش ناموفق ممکن است زمان پاسخ نهایی را افزایش دهد.</li>
  <li>در صورت خرابی همهٔ ارائه‌دهندگان، درخواست با خطا مواجه می‌شود.</li>
  <li>این ابزار هزینهٔ سرویس‌های پولی را حذف نمی‌کند.</li>
</ul>

<hr>

<h2 dir="rtl" align="right">سهم انجام‌شده در پروژهٔ دانشگاهی</h2>

<ul dir="rtl" align="right">
  <li>دریافت و نصب پروژه روی ویندوز</li>
  <li>بررسی ساختار و نحوهٔ اجرای پروژه</li>
  <li>ساخت و تنظیم فایل محیطی</li>
  <li>تولید کلید رمزنگاری</li>
  <li>اجرای پروژه با روش محلی و کانتینری</li>
  <li>افزودن ارائه‌دهندگان</li>
  <li>بررسی سلامت کلیدها</li>
  <li>ساخت کلید یکپارچه</li>
  <li>تنظیم مدل‌ها و مسیر جایگزین</li>
  <li>آزمایش درخواست‌ها</li>
  <li>بررسی گزارش‌ها و آمار</li>
  <li>اتصال به <code>Cline</code></li>
  <li>آزمایش رابط سازگار با <code>OpenAI</code></li>
  <li>رفع خطاهای اجرایی</li>
  <li>تهیهٔ مستندات و ویدیوی آموزشی</li>
</ul>

<hr>

<h2 dir="rtl" align="right">پرسش‌های آماده برای ارائه</h2>

<h3 dir="rtl" align="right"><code>FreeLLMAPI</code> چه کاری انجام می‌دهد؟</h3>

<p dir="rtl" align="right">
چند ارائه‌دهنده و چند مدل هوش مصنوعی را پشت یک رابط سازگار با
<code>OpenAI</code>
مدیریت می‌کند. برنامهٔ مصرف‌کننده فقط به یک نشانی پایه، یک کلید یکپارچه و یک شناسهٔ مدل نیاز دارد.
</p>

<h3 dir="rtl" align="right">تفاوت آن با اتصال مستقیم به یک رابط چیست؟</h3>

<p dir="rtl" align="right">
در اتصال مستقیم، برنامه به یک ارائه‌دهنده وابسته است. در این پروژه می‌توان چند ارائه‌دهنده و چند مدل را مدیریت و برای آن‌ها ترتیب جایگزین تعریف کرد.
</p>

<h3 dir="rtl" align="right">سهم دانشجو در پروژه چیست؟</h3>

<p dir="rtl" align="right">
سهم انجام‌شده شامل نصب، پیکربندی، اتصال ارائه‌دهندگان، بررسی سلامت کلیدها، تنظیم مسیر جایگزین، اتصال به
<code>Cline</code>
، آزمایش رابط، رفع خطا، مستندسازی و تهیهٔ ویدیوی آموزشی است.
</p>

<h3 dir="rtl" align="right">آیا این ابزار همهٔ مدل‌ها را رایگان می‌کند؟</h3>

<p dir="rtl" align="right">
خیر. این ابزار فقط مدل‌ها و سهمیه‌هایی را مدیریت می‌کند که ارائه‌دهندگان به‌صورت رسمی در اختیار کاربر قرار داده‌اند.
</p>

<h3 dir="rtl" align="right">کلید یکپارچه چیست؟</h3>

<p dir="rtl" align="right">
کلیدی است که برنامه‌ای مانند
<code>Cline</code>
برای اتصال به
<code>FreeLLMAPI</code>
استفاده می‌کند؛ در نتیجه، کلید واقعی ارائه‌دهندگان در اختیار برنامهٔ مصرف‌کننده قرار نمی‌گیرد.
</p>

<h3 dir="rtl" align="right">مسیر جایگزین چیست؟</h3>

<p dir="rtl" align="right">
اگر مدل یا ارائه‌دهندهٔ اول نتواند پاسخ دهد، درخواست به مدل بعدی فرستاده می‌شود.
</p>

<hr>

<h2 dir="rtl" align="right">ساختار پیشنهادی مخزن</h2>

```text
freellmapi-university-project/
├── README.md
├── .gitignore
├── THIRD_PARTY_NOTICES.md
├── docs/
│   └── INSTALL-FA.md
├── scripts/
│   └── setup-freellmapi.ps1
└── screenshots/
    ├── dashboard.png
    ├── provider-keys.png
    ├── fallback.png
    ├── playground.png
    ├── analytics.png
    └── cline-connection.png
```

<blockquote dir="rtl">
قبل از انتشار تصاویر، تمام کلیدها، رمزها و اطلاعات حساب‌ها را حذف یا محو کنید.
</blockquote>

<hr>

<h2 dir="rtl" align="right">لینک‌های پروژه</h2>

<p dir="rtl" align="right">
<strong>ویدیوی آنلاین:</strong>
<a href="https://drive.google.com/file/d/1yDVhFRk7pRmxaFJIKEIIzoiOmvJRG-IQ/preview">
مشاهدهٔ مستقیم ویدیوی پروژه
</a>
</p>

<p dir="rtl" align="right">
<strong>نسخهٔ قابل دانلود:</strong>
<a href="https://github.com/Amir200382/freellmapi-university-project/releases/tag/v1.0.0">
انتشار نسخهٔ ۱٫۰٫۰
</a>
</p>

<p dir="rtl" align="right">
<strong>مخزن اصلی:</strong>
<a href="https://github.com/tashfeenahmed/freellmapi">
github.com/tashfeenahmed/freellmapi
</a>
</p>

<hr>

<h2 dir="rtl" align="right">اعتبار پروژه</h2>

<p dir="rtl" align="right">
تمام حقوق کد اصلی، نام پروژه و مستندات
<code>FreeLLMAPI</code>
متعلق به نویسندگان و مشارکت‌کنندگان مخزن اصلی است.
</p>

<p dir="rtl" align="right">
این مخزن با هدف ارائهٔ دانشگاهی، آموزش نصب، پیکربندی، آزمایش عملی و مستندسازی پروژه ایجاد شده و ادعای مالکیت بر سورس اصلی ندارد.
</p>
