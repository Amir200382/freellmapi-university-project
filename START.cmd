@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FreeLLM Studio - University Edition

where py >nul 2>nul
if not errorlevel 1 (
  set "PY=py -3"
  goto :python_ok
)

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERROR] Python 3.10+ was not found.
  echo Install Python from https://www.python.org/downloads/ and enable "Add Python to PATH".
  echo.
  pause
  exit /b 1
)
set "PY=python"

:python_ok
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating isolated Python environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)

set "VPY=.venv\Scripts\python.exe"

echo [2/3] Checking dependencies...
"%VPY%" -c "import PySide6, requests, socks" >nul 2>nul
if errorlevel 1 (
  echo Installing UI and HTTP dependencies. This happens once...
  "%VPY%" -m pip install --disable-pip-version-check --upgrade pip
  if errorlevel 1 goto :fail
  "%VPY%" -m pip install --disable-pip-version-check -r requirements.txt
  if errorlevel 1 goto :fail
)

echo [3/3] Starting FreeLLM Studio...
"%VPY%" app.py
set "APP_RC=%ERRORLEVEL%"
if not "%APP_RC%"=="0" (
  echo.
  echo [ERROR] FreeLLM Studio exited unexpectedly. Exit code: %APP_RC%
  echo Crash log: %LOCALAPPDATA%\FreeLLMStudio\logs\crash.log
  echo Runtime log: %LOCALAPPDATA%\FreeLLMStudio\logs\studio.log
  echo.
  if exist "%LOCALAPPDATA%\FreeLLMStudio\logs\crash.log" (
    echo -------- crash.log --------
    type "%LOCALAPPDATA%\FreeLLMStudio\logs\crash.log"
    echo ---------------------------
  )
  pause
)
exit /b %APP_RC%

:fail
echo.
echo [ERROR] Setup failed. Review the messages above.
echo.
pause
exit /b 1
