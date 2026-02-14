@echo off
setlocal
title TESS AI Supervisor
color 0b

:: Get the directory of this script
cd /d "%~dp0"

echo --------------------------------------------------
echo          STARTING TESS TERMINAL PRO
echo --------------------------------------------------

:: Check if .venv exists
if not exist ".venv" (
    echo [ERROR] Virtual environment not found.
    echo Please run 'setup.ps1' first!
    pause
    exit /b
)

:: Activate Venv and Run Supervisor
echo [LAUNCHER] Activating Brain...
call .venv\Scripts\activate.bat

echo [LAUNCHER] Starting Supervisor...
python supervisor.py

:: If it crashes/exits, pause so user can see error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] TESS exited with code %ERRORLEVEL%
    pause
)
