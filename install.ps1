# TESS Terminal Pro Installer
# Run via: irm https://raw.githubusercontent.com/Rohit978/tess/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$AppName = "TESS"
$RepoUrl = "https://api.github.com/repos/Rohit978/tess/releases/latest"
$InstallDir = "$env:USERPROFILE\.tess-bin"
$ExePath = "$InstallDir\tess.exe"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "       Installing TESS Terminal Pro" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Create hidden directory
if (-not (Test-Path $InstallDir)) {
    Write-Host "-> Creating installation directory at $InstallDir..."
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
}

# 2. Get Latest Download URL from GitHub Releases
Write-Host "-> Finding latest release..."
try {
    $Release = Invoke-RestMethod -Uri $RepoUrl
    $Asset = $Release.assets | Where-Object { $_.name -eq "TESS.exe" }
    
    if (-not $Asset) {
        Write-Error "Could not find 'TESS.exe' in the latest GitHub release."
        exit 1
    }
    
    $DownloadUrl = $Asset.browser_download_url
    $Version = $Release.tag_name
    Write-Host "-> Version found: $Version"
} catch {
    Write-Error "Failed to check GitHub releases. Are you sure 'Rohit978/tess' is public and has a release?"
    exit 1
}

# 3. Download the EXE
Write-Host "-> Downloading TESS.exe (this may take a minute)..."
Invoke-WebRequest -Uri $DownloadUrl -OutFile $ExePath
Write-Host "-> Download complete."

# 4. Add to PATH
Write-Host "-> Adding TESS to your system PATH..."

$UserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$Paths = $UserPath -split ";"

if ($InstallDir -notin $Paths) {
    if ($UserPath -match ";$") {
        $NewPath = $UserPath + $InstallDir
    } else {
        $NewPath = $UserPath + ";" + $InstallDir
    }
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    Write-Host "-> Added $InstallDir to PATH." -ForegroundColor Green
    $PathUpdated = $true
} else {
    Write-Host "-> TESS is already in your PATH."
    $PathUpdated = $false
}

Write-Host ""
Write-Host "✅ Installation Successful!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan

if ($PathUpdated) {
    Write-Host "IMPORTANT: You must restart your terminal for the changes to take effect." -ForegroundColor Yellow
}

Write-Host "Once ready, type 'tess init' to begin your setup." -ForegroundColor White
Write-Host ""
