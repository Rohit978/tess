# scan_commands.ps1
# Scans for executable commands and filters them for TESS RAG indexing.

$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::UTF8

Write-Host "Scanning for commands..."

# 1. Get All Application Commands
$cmds = Get-Command -CommandType Application -ErrorAction SilentlyContinue

# 2. Filter Logic
# We want: 
# - Tools in PATH (Git, Python, Node, etc.)
# - Tools in Program Files (User installed)
# - Core System Utils (System32 - selective)

$filtered = @()
$seen = @{}

# Whitelist of interesting system tools to ensure we capture
$whitelist = @("ping", "ipconfig", "net", "tasklist", "shutdown", "curl", "ssh", "scp", "tar", "where", "whoami", "systeminfo")

foreach ($cmd in $cmds) {
    $name = $cmd.Name.ToLower().Replace(".exe", "")
    $path = $cmd.Source
    
    # Skip duplicates
    if ($seen.ContainsKey($name)) { continue }
    
    $keep = $false
    
    # Criteria A: Is it in the whitelist?
    if ($whitelist -contains $name) { $keep = $true }
    
    # Criteria B: Is it a common dev tool? (git, python, npm, node, docker, etc.)
    if ($name -match "^(git|python|pip|npm|node|docker|java|javac|go|rustc|cargo|code|cursor|ffmpeg|ffprobe|adb|fastboot)$") { $keep = $true }
    
    # Criteria C: Is it in Program Files? (User installed apps usually live here)
    if ($path -match "Program Files") { 
        # But exclude uninstaller/helper junk
        if ($name -notmatch "(uninstall|helper|update|crash|reporter|agent|service|setup|installer)") {
            $keep = $true 
        }
    }
    
    if ($keep) {
        $seen[$name] = $true
        $filtered += @{
            Name = $name
            Path = $path
            Version = $cmd.Version
        }
    }
}

# Output as JSON
$filtered | ConvertTo-Json -Depth 2
