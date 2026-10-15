[CmdletBinding()]
param(
    [switch]$Run,
    [switch]$Development
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VirtualPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Requirements = Join-Path $ProjectRoot "requirements-dev.txt"

Set-Location $ProjectRoot

$PythonCommand = Get-Command py -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
}

if (-not $PythonCommand) {
    throw "Python was not found. Install Python 3.10 or newer from python.org."
}

if (-not (Test-Path -LiteralPath $VirtualPython)) {
    Write-Host "Creating virtual environment..."
    if ($PythonCommand.Name -eq "py.exe" -or $PythonCommand.Name -eq "py") {
        & $PythonCommand.Source -3 -m venv (Join-Path $ProjectRoot ".venv")
    }
    else {
        & $PythonCommand.Source -m venv (Join-Path $ProjectRoot ".venv")
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed with exit code $LASTEXITCODE."
    }
}

$PythonVersion = & $VirtualPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$PythonVersion -lt [version]"3.10") {
    throw "Python 3.10 or newer is required. Found: $PythonVersion"
}

Write-Host "Installing dependencies..."
& $VirtualPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed with exit code $LASTEXITCODE."
}
& $VirtualPython -m pip install --requirement $Requirements
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "Setup completed successfully." -ForegroundColor Green
Write-Host "Tests:  .\.venv\Scripts\python.exe -m pytest"
Write-Host "Run:    .\.venv\Scripts\python.exe .\src\main.py"
Write-Host "Build:    .\build.ps1"

if ($Run) {
    if ($Development) {
        $env:DEV_BACKUP_ENV = "development"
    }
    & $VirtualPython (Join-Path $ProjectRoot "src\main.py")
}
