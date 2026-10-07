[CmdletBinding()]
param(
    [switch]$Installer
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VirtualPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$SpecFile = Join-Path $ProjectRoot "packaging\DevProjectBackup.spec"

Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath $VirtualPython)) {
    throw ".venv was not found. Run .\setup.cmd first."
}

& $VirtualPython -m PyInstaller --noconfirm --clean $SpecFile
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

if ($Installer) {
    $CompilerCommand = Get-Command iscc -ErrorAction SilentlyContinue
    $CompilerPath = if ($CompilerCommand) { $CompilerCommand.Source } else { $null }
    if (-not $CompilerPath) {
        $DefaultCompiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
        if (Test-Path -LiteralPath $DefaultCompiler) {
            $CompilerPath = $DefaultCompiler
        }
    }
    if (-not $CompilerPath) {
        throw "Inno Setup 6 was not found. Install it or run without -Installer."
    }
    & $CompilerPath (Join-Path $ProjectRoot "packaging\DevProjectBackup.iss")
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE."
    }
}

Write-Host "Build completed successfully." -ForegroundColor Green
