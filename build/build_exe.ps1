# Build Edytor.exe + EdytorBE.exe + EdytorFE.exe (Windows)
#
# Wymaga: pip install pyinstaller
# Uruchom z roota repo:
#   powershell -ExecutionPolicy Bypass -File build/build_exe.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    $Py = "python"
}

& $Py -m pip install pyinstaller --quiet
& $Py -m PyInstaller build/Edytor.spec --noconfirm --distpath dist --workpath build/pyinstaller

Write-Host ""
Write-Host "Gotowe: dist/Edytor.exe, dist/EdytorBE.exe, dist/EdytorFE.exe"
Write-Host "Skopiuj caly folder dist obok siebie i uruchom Edytor.exe"
Write-Host "Klucz AI: %LOCALAPPDATA%\Edytor\.env (skopiuj z .env.example)"
