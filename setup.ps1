# TESS Terminal Pro - Universal Installer
# Usage: Right-click -> Run with PowerShell

Write-Host "--------------------------------------------------" -ForegroundColor Cyan
Write-Host "      TESS TERMINAL PRO - SETUP WIZARD (v5.0)     " -ForegroundColor Cyan
Write-Host "--------------------------------------------------" -ForegroundColor Cyan

# 1. Dependency Check
Write-Host "`n[1/5] Checking Dependencies..."
$pythonInstalled = Get-Command python -ErrorAction SilentlyContinue
$gitInstalled = Get-Command git -ErrorAction SilentlyContinue

if (-not $pythonInstalled) {
    Write-Host "❌ Python is NOT installed." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from python.org or run: winget install python"
    Pause
    Exit
} else {
    Write-Host "✅ Python found." -ForegroundColor Green
}

if (-not $gitInstalled) {
    Write-Host "⚠️  Git is NOT installed. You won't be able to update TESS easily." -ForegroundColor Yellow
} else {
    Write-Host "✅ Git found." -ForegroundColor Green
}

# 2. Virtual Environment Setup
Write-Host "`n[2/5] Setting up Virtual Environment..."
if (-not (Test-Path ".venv")) {
    Write-Host "Creating .venv..."
    python -m venv .venv
} else {
    Write-Host ".venv already exists."
}

# Activate Venv
$venvPath = ".venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    # Check execution policy
    try {
        & $venvPath
        Write-Host "✅ Virtual Environment Activated." -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Could not activate venv globally. Trying local scope..." -ForegroundColor Yellow
        try {
            . $venvPath
        } catch {
            Write-Host "EXECUTION POLICY ERROR: Run PowerShell as Admin and type: Set-ExecutionPolicy RemoteSigned" -ForegroundColor Red
            Pause
            Exit
        }
    }
} else {
    Write-Host "❌ Failed to create/find virtual environment." -ForegroundColor Red
    Pause
    Exit
}

# 3. Install Dependencies
Write-Host "`n[3/5] Installing Libraries (this may take a minute)..."
python -m pip install --upgrade pip
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Dependency Installation Failed." -ForegroundColor Red
    Pause
    Exit
}
Write-Host "✅ Dependencies Installed." -ForegroundColor Green

# 4. LLM Configuration (Interactive)
Write-Host "`n[4/5] Configuring Your AI Brain..."

$envFile = ".env"
$envContent = ""

# Determine Provider
Write-Host "Select your Primary Intelligence Provider:"
Write-Host "[1] Groq (Recommended - Free & Fast)" -ForegroundColor Cyan
Write-Host "[2] Gemini (Google - Large Context)" -ForegroundColor Cyan
Write-Host "[3] OpenAI (GPT-4 - Standard)" -ForegroundColor Cyan
Write-Host "[4] DeepSeek (Coding Specialist)" -ForegroundColor Cyan

$choice = Read-Host "Enter Choice [1-4]"

$provider = "groq"
$keyName = "GROQ_API_KEY"

switch ($choice) {
    "1" { $provider = "groq"; $keyName = "GROQ_API_KEY" }
    "2" { $provider = "gemini"; $keyName = "GEMINI_API_KEY" }
    "3" { $provider = "openai"; $keyName = "OPENAI_API_KEY" }
    "4" { $provider = "deepseek"; $keyName = "DEEPSEEK_API_KEY" }
    Default { Write-Host "Invalid choice, defaulting to Groq." }
}

Write-Host "You selected: $provider" -ForegroundColor Yellow
$apiKey = Read-Host "Enter your $keyName (Hidden keys not supported in simple terminal)"

# Create .env content
$envContent = @"
# TESS Configuration (Auto-Generated)
LLM_PROVIDER=$provider
LLM_MODEL=auto
$keyName=$apiKey
SAFE_MODE=True
SECURITY_LEVEL=MEDIUM
"@

Set-Content -Path $envFile -Value $envContent
Write-Host "✅ Configuration saved to $envFile." -ForegroundColor Green

# 5. Create Desktop Shortcut
Write-Host "`n[5/6] Creating Desktop Shortcut..."
$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\TESS AI.lnk")
$Shortcut.TargetPath = "$PWD\Start_TESS.bat"
$Shortcut.WorkingDirectory = "$PWD"
$Shortcut.IconLocation = "shell32.dll,23" # Help/Question Icon (or use a custom .ico if available)
$Shortcut.Save()
Write-Host "✅ Shortcut 'TESS AI' created on Desktop." -ForegroundColor Green

# 6. Launch
Write-Host "`n[6/6] Launching TESS..."
Write-Host "--------------------------------------------------" -ForegroundColor Cyan
Wait-Event -Timeout 2

# Use Supervisor for production robustness
cmd /c Start_TESS.bat
