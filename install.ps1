param(
    [switch]$CleanLegacy
)

# PaperSpine V4 installer (Windows). Thin wrapper that delegates all file work to
# the Python sync, which generates dist/ from src/ and installs the single
# `paper-spine` skill into Claude Code, Codex, OpenClaw, and Hermes.
#
# PowerShell 5.1-safe by design: no PS7-only operators, and it NEVER writes
# settings.json (fixes issue #3 — old installers could wipe settings.json).

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Sync = Join-Path $Root "src\scripts\sync_local_installs.py"

if (-not (Test-Path -LiteralPath $Sync)) {
    throw "PaperSpine sync script not found: $Sync"
}

# Resolve a REAL Python >= 3.10. Skip the Microsoft Store WindowsApps
# execution-alias stub (present by default when Python was installed via the
# py launcher only) and confirm each candidate actually runs at a supported
# version, rather than trusting the first Get-Command hit.
$python = $null
foreach ($candidate in @("python", "python3", "py")) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    if ($cmd.Source -and $cmd.Source -like "*\WindowsApps\*") { continue }
    try {
        $ver = & $cmd.Source -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
    } catch { continue }
    if ($LASTEXITCODE -ne 0 -or -not $ver) { continue }
    $parts = $ver.Trim().Split(".")
    if (([int]$parts[0] -gt 3) -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 10)) {
        $python = $cmd.Source
        break
    }
}
if (-not $python) {
    throw "Python 3.10+ not found on PATH. Install Python 3.10 or newer and retry."
}

$args = @($Sync)
if ($CleanLegacy) { $args += "--clean-legacy" }

Write-Output "Installing PaperSpine V4 (single skill, 4 hosts) via $python ..."
& $python @args
if ($LASTEXITCODE -ne 0) {
    throw "PaperSpine install failed (exit $LASTEXITCODE)."
}
Write-Output "PaperSpine V4 installed. In Claude Code or Codex, run /paperspine to start."
