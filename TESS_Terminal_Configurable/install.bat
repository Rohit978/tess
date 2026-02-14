@echo off
echo ==========================================
echo    TESS Terminal - Configurable Edition
echo           Installation Script
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo [1/3] Python found
echo.

REM Install dependencies
echo [2/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [3/3] Installation complete!
echo.
echo ==========================================
echo   Next steps:
echo   1. Run: tess --setup
echo   2. Follow the wizard to configure
echo   3. Run: tess
echo ==========================================
echo.
pause
