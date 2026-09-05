$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$pythonw = Join-Path $PSScriptRoot '.venv/Scripts/pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) {
    throw 'Run setup.ps1 first to install the project environment.'
}
$devRuntime = Join-Path $PSScriptRoot '.runtime/test-panel'
New-Item -ItemType Directory -Path $devRuntime -Force | Out-Null
$probe = @'
from pathlib import Path
import sys
from bg3_helper.core import BridgeError
from bg3_helper.transport import request
try:
    request(Path(sys.argv[1]), 'status')
except BridgeError:
    print('stopped')
else:
    print('running')
'@
$devState = & $python -c $probe $devRuntime
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the development companion.' }
if ($devState -eq 'running') {
    Write-Host 'The development companion is already running. Use the BG3 Companion - Test window.'
    exit 0
}
# Reuse the current conversation destination, without copying its input permission or token.
$normalSession = Join-Path $PSScriptRoot '.runtime/session.json'
if (Test-Path -LiteralPath $normalSession) {
    Copy-Item -LiteralPath $normalSession -Destination (Join-Path $devRuntime 'session.json')
}
$arenaCount = & $python -c 'from bg3_helper.windows import WindowsDesktop; print(len(WindowsDesktop(test_target=True).windows()))'
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the disposable test arena.' }
if ([int]$arenaCount -eq 0) {
    Start-Process -FilePath $pythonw -ArgumentList '-m bg3_helper.test_arena' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
}
Start-Process -FilePath $pythonw -ArgumentList '-m bg3_helper --runtime .runtime/test-panel panel --test-target' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardError (Join-Path $devRuntime 'panel-stderr.log')
Write-Host 'Development companion opened. Captures, profiles, and save associations are isolated under .runtime/test-panel.'
