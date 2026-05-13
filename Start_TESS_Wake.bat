@echo off
setlocal
title TESS Wake Listener
color 0e

cd /d "%~dp0"

echo --------------------------------------------------
echo       STARTING TESS WAKE LISTENER
echo --------------------------------------------------

if not exist ".venv" (
    echo [ERROR] Virtual environment not found.
    echo Please run setup.ps1 first.
    pause
    exit /b
)

call .venv\Scripts\activate.bat

:WAKE_LOOP
python -m tess_cli.scripts.wake_listener --start-script "%~dp0Start_TESS.bat"
if %ERRORLEVEL% EQU 0 (
    echo [WAKE] Listener exited normally.
    exit /b 0
)

echo [WAKE] Listener crashed (code %ERRORLEVEL%). Restarting in 3 seconds...
timeout /t 3 /nobreak >nul
goto WAKE_LOOP
