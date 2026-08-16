@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FreeLLM Studio - Self Test

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py --self-test
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 app.py --self-test
  ) else (
    python app.py --self-test
  )
)

echo.
if errorlevel 1 (
  echo SELF-TEST FAILED
) else (
  echo SELF-TEST PASSED
)
echo.
pause
