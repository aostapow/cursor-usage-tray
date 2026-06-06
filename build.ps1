$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.14 -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt
}

.\.venv\Scripts\pip install -r requirements-build.txt

Get-Process cursor-usage-tray, cursor-usage-float -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 500

$distTray = Join-Path $root "dist\cursor-usage-tray"
$distFloat = Join-Path $root "dist\cursor-usage-float"

if (Test-Path $distTray) { Remove-Item -Recurse -Force $distTray }
if (Test-Path $distFloat) { Remove-Item -Recurse -Force $distFloat }

.\.venv\Scripts\pyinstaller.exe --noconfirm cursor-usage-tray.spec
.\.venv\Scripts\pyinstaller.exe --noconfirm cursor-usage-float.spec

Copy-Item -Force (Join-Path $root "Iniciar.cmd") (Join-Path $distTray "Iniciar.cmd")

$floatTarget = Join-Path $distTray "float"
New-Item -ItemType Directory -Force -Path $floatTarget | Out-Null
Copy-Item -Recurse -Force (Join-Path $distFloat "*") $floatTarget

$version = (Select-String -Path (Join-Path $root "src\__version__.py") -Pattern '__version__ = "([^"]+)"').Matches[0].Groups[1].Value
$zipName = "cursor-usage-tray-v$version-windows.zip"
$zipPath = Join-Path $root "dist\$zipName"
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path (Join-Path $distTray "*") -DestinationPath $zipPath -Force

Write-Host ""
Write-Host "Build listo:"
Write-Host "  Tray:  $(Join-Path $distTray 'cursor-usage-tray.exe')"
Write-Host "  Float: $(Join-Path $floatTarget 'cursor-usage-float.exe')"
Write-Host "  Zip:   $zipPath"
Write-Host "Usar Iniciar.cmd si Windows bloquea el .exe descargado de Internet."
