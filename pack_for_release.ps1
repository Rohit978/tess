# TESS Release Packer
# Creates a clean ZIP file to share with others
# Excludes: .venv, .env, __pycache__, user memory

$Version = "v5.0"
$ZipName = "TESS_Terminal_Pro_$Version.zip"
$Source = "$PSScriptRoot"
$TempDir = "$PSScriptRoot\TESS_Release_Temp"

Write-Host "📦 Packaging TESS for Release..." -ForegroundColor Cyan

# 1. Create Temp Directory
if (Test-Path $TempDir) { Remove-Item -Recurse -Force $TempDir }
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

# 2. Copy Core Files
$FilesToCopy = @(
    "src",
    "requirements.txt",
    "setup.ps1",
    "Install_TESS.bat",
    "supervisor.py",
    "main.py",
    "Start_TESS.bat"
)

foreach ($file in $FilesToCopy) {
    Copy-Item -Recurse -Path "$Source\$file" -Destination "$TempDir"
}

# 3. Create README for new user
$ReadmeContent = @"
WELCOME TO TESS TERMINAL PRO ($Version)
----------------------------------------

INSTALLATION:
1. Extract this ZIP file.
2. Right-Click 'setup.ps1' -> Run with PowerShell.
3. Follow the instructions to set up your AI Brain.

LAUNCHING:
- Double-click 'Start_TESS.bat' (or the Desktop Shortcut created by setup).

ENJOY!
"@
Set-Content -Path "$TempDir\README.txt" -Value $ReadmeContent

# 4. Clean up junk (pycache) from Temp
Get-ChildItem -Path $TempDir -Recurse -Include "__pycache__", "*.pyc" | Remove-Item -Recurse -Force

# 5. Zip it
if (Test-Path $ZipName) { Remove-Item -Force $ZipName }
Compress-Archive -Path "$TempDir\*" -DestinationPath "$Source\$ZipName"

# 6. Cleanup Temp
Remove-Item -Recurse -Force $TempDir

Write-Host "✅ Release Ready: $ZipName" -ForegroundColor Green
Write-Host "You can now send this ZIP file to anyone!" -ForegroundColor Yellow
