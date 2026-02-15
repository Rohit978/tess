# scan_commands.ps1
# Scans for executable commands and filters them for TESS RAG indexing.

$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::UTF8

Write-Host "Scanning for commands..."

# 1. Get All Commands (Cmdlets, Functions, Aliases, External Apps)
$cmds = Get-Command -CommandType Cmdlet, Function, Alias, Application -ErrorAction SilentlyContinue

$filtered = @()
$seen = @{}

foreach ($cmd in $cmds) {
    if ($cmd.Name -match "^(_|prompt|tabexpansion|oss-)") { continue }
    
    $name = $cmd.Name.ToLower()
    $type = $cmd.CommandType.ToString()
    
    # Skip duplicates (prefer Aliases/Cmdlets over Apps if name matches)
    if ($seen.ContainsKey($name)) { continue }
    $seen[$name] = $true

    $info = @{
        Name = $name
        Type = $type
        Source = $cmd.Source
        Version = $cmd.Version.ToString()
    }

    # For Aliases, get the target definition
    if ($type -eq "Alias") {
        $info.Definition = $cmd.Definition
    }

    $filtered += $info
}

# Output as JSON
$filtered | ConvertTo-Json -Depth 2
