# Changelog

## 1.2.1
- حذف وابستگی PowerShell/.NET/DPAPI از مسیر ذخیره API Key برای سازگاری بیشتر با Windows.
- مدیریت کنترل‌شده تنظیمات قدیمی Secret.
- حفظ نتیجه Test موفق Provider حتی در صورت خطای ذخیره تنظیمات محلی.

## 1.2.0
- اضافه شدن Network routing مناسب VPN/Proxy.
- پشتیبانی از System Proxy، Environment Proxy، TUN و Manual Proxy.
- bypass شدن localhost برای Local Model و Bridge.

## 1.1.1
- هماهنگ شدن Test موفق Provider با Chat.
- ذخیره Model معتبر و فعال شدن Provider پس از inference موفق.

## 1.1.0
- پایدارسازی Workerهای PySide6.
- جلوگیری از اجرای هم‌زمان عملیات Provider.
- بهبود Crash Logging.

## 1.0.3
- Ready شدن Local Model فقط پس از health/inference واقعی.
- مدیریت بهتر تداخل پورت Local Model.
