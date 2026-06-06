@echo off
REM Desbloquea archivos descargados de Internet (Mark of the Web) y abre la app.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-ChildItem -LiteralPath '%~dp0' -Recurse -File | ForEach-Object { Unblock-File -LiteralPath $_.FullName -ErrorAction SilentlyContinue }"
start "" "%~dp0cursor-usage-tray.exe"
