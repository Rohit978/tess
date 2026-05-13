@echo off
setlocal
title Enable TESS Always-On
color 0a

cd /d "%~dp0"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_DIR%\TESS Wake Listener.lnk"

echo --------------------------------------------------
echo      ENABLING TESS ALWAYS-ON WAKE LISTENER
echo --------------------------------------------------

if not exist "%~dp0Start_TESS_Wake.bat" (
    echo [ERROR] Start_TESS_Wake.bat not found in this folder.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$ws=New-Object -ComObject WScript.Shell; $sc=$ws.CreateShortcut('%SHORTCUT_PATH%'); $sc.TargetPath='%~dp0Start_TESS_Wake.bat'; $sc.WorkingDirectory='%~dp0'; $sc.IconLocation='shell32.dll,23'; $sc.Save()"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create startup shortcut.
    pause
    exit /b 1
)

echo [OK] Always-on wake listener enabled.
echo [INFO] It will start automatically after you log in.
echo [INFO] Starting listener now...
start "" "%~dp0Start_TESS_Wake.bat"
exit /b 0

