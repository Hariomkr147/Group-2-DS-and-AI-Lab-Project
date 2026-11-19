$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& (Join-Path $PSScriptRoot '..\Ncert work\.venv\Scripts\python.exe') prepare_data.py
if ($LASTEXITCODE -ne 0) { throw 'Pilot preparation failed' }
& (Join-Path $PSScriptRoot '..\Ncert work\.venv\Scripts\python.exe') -m uvicorn server:app --host 127.0.0.1 --port 8765
