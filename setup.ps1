$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Could not create the project Python environment.' }
& ./.venv/Scripts/python.exe -m pip install -e '.[test]'
if ($LASTEXITCODE -ne 0) { throw 'Could not install project dependencies.' }
