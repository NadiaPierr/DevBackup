[CmdletBinding()]
param(
    [switch]$Installer
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VirtualPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$SpecFile = Join-Path $ProjectRoot "packaging\DevProjectBackup.spec"
$VersionFile = Join-Path $ProjectRoot "src\version.py"
$VersionInfoFile = Join-Path $ProjectRoot "packaging\generated_version_info.txt"

Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath $VirtualPython)) {
    throw ".venv was not found. Run .\setup.cmd first."
}

$VersionSource = Get-Content -Raw -LiteralPath $VersionFile
$VersionMatch = [regex]::Match($VersionSource, '__version__\s*=\s*"(?<version>\d+\.\d+\.\d+)"')
if (-not $VersionMatch.Success) {
    throw "Could not read a semantic version from src\version.py."
}
$AppVersion = $VersionMatch.Groups["version"].Value
$VersionParts = $AppVersion.Split(".")

$VersionInfo = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($($VersionParts[0]), $($VersionParts[1]), $($VersionParts[2]), 0),
    prodvers=($($VersionParts[0]), $($VersionParts[1]), $($VersionParts[2]), 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable("040904B0", [
        StringStruct("CompanyName", "Dev Project Backup"),
        StringStruct("FileDescription", "Local project backup manager"),
        StringStruct("FileVersion", "$AppVersion"),
        StringStruct("InternalName", "DevProjectBackup"),
        StringStruct("OriginalFilename", "DevProjectBackup.exe"),
        StringStruct("ProductName", "Dev Project Backup"),
        StringStruct("ProductVersion", "$AppVersion"),
      ])
    ]),
    VarFileInfo([VarStruct("Translation", [1033, 1200])]),
  ],
)
"@
[System.IO.File]::WriteAllText($VersionInfoFile, $VersionInfo, [System.Text.UTF8Encoding]::new($false))

Write-Host "Building Dev Project Backup $AppVersion..."

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
    & $CompilerPath "/DMyAppVersion=$AppVersion" (Join-Path $ProjectRoot "packaging\DevProjectBackup.iss")
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE."
    }
}

Write-Host "Build completed successfully." -ForegroundColor Green
