$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.14 -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt
}

.\.venv\Scripts\pip install -r requirements-build.txt

Get-Process cursor-usage-tray -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 500

.\.venv\Scripts\pyinstaller.exe --noconfirm cursor-usage-tray.spec

Copy-Item -Force (Join-Path $root "Iniciar.cmd") (Join-Path $root "dist\cursor-usage-tray\Iniciar.cmd")

$exe = Join-Path $root "dist\cursor-usage-tray\cursor-usage-tray.exe"
Write-Host ""
Write-Host "Build listo: $exe"
Write-Host "Usar Iniciar.cmd si Windows bloquea el .exe descargado de Internet."
