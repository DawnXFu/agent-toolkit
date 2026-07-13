[CmdletBinding()]
param(
    [ValidateSet("User", "Project")][string]$Scope = "User",
    [ValidateSet("All", "Claude", "Codex", "OpenCode", "Generic")][string]$Agent = "All",
    [string]$ProjectRoot = (Get-Location).Path,
    [switch]$Link
)

$ErrorActionPreference = "Stop"
$SourceDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ($Scope -eq "User") {
    $SharedDest = Join-Path $HOME ".agents\skills\unified-handoff"
    $ClaudeDest = Join-Path $HOME ".claude\skills\unified-handoff"
} else {
    $ResolvedProject = (Resolve-Path $ProjectRoot).Path
    $SharedDest = Join-Path $ResolvedProject ".agents\skills\unified-handoff"
    $ClaudeDest = Join-Path $ResolvedProject ".claude\skills\unified-handoff"
}

function Install-SkillCopy {
    param([Parameter(Mandatory = $true)][string]$Destination)
    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    if (Test-Path $Destination) { Remove-Item $Destination -Recurse -Force }
    if ($Link) {
        New-Item -ItemType SymbolicLink -Path $Destination -Target $SourceDir | Out-Null
    } else {
        Copy-Item $SourceDir -Destination $Destination -Recurse -Force
    }
    Write-Output "Installed: $Destination"
}

switch ($Agent) {
    "Claude" { Install-SkillCopy $ClaudeDest }
    { $_ -in @("Codex", "OpenCode", "Generic") } { Install-SkillCopy $SharedDest }
    "All" { Install-SkillCopy $SharedDest; Install-SkillCopy $ClaudeDest }
}
