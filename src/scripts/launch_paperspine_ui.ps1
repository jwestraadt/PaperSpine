param(
    [string]$OutputDir = "paper_rewriting_output",
    [switch]$InPlace
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$wizard = Join-Path $scriptDir "intake_wizard.py"

if (-not (Test-Path -LiteralPath $wizard)) {
    throw "PaperSpine intake wizard not found: $wizard"
}

# Resolve a REAL Python >= 3.10, matching install.ps1: skip the WindowsApps
# Store stub and confirm the interpreter runs at a supported version instead
# of trusting a bare `python` (which may be the stub or absent from PATH).
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

if ($InPlace) {
    chcp 65001 > $null
    $env:PYTHONUTF8 = "1"
    $OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
    & $python $wizard --keyboard-ui --output-dir $OutputDir
    exit $LASTEXITCODE
}

$cwd = (Get-Location).Path
$escapedCwd = $cwd.Replace("'", "''")
$escapedWizard = $wizard.Replace("'", "''")
$escapedOutput = $OutputDir.Replace("'", "''")
$escapedPython = $python.Replace("'", "''")

$command = @"
Set-Location -LiteralPath '$escapedCwd'
chcp 65001 > `$null
`$env:PYTHONUTF8 = '1'
`$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
& '$escapedPython' '$escapedWizard' --keyboard-ui --output-dir '$escapedOutput'
Write-Host ''
Write-Host 'PaperSpine intake finished. Config files are in: $escapedOutput'
Write-Host 'Close this window after checking the result.'
"@

Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $command
)
