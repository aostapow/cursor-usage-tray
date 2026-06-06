$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.14 -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt
}

.\.venv\Scripts\python.exe -m src.float_main @args
