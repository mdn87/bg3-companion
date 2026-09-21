$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
try {
    . (Join-Path $PSScriptRoot 'scripts/bootstrap.ps1')
} catch {
    $shell = New-Object -ComObject WScript.Shell
    $shell.Popup('Launcher resources are missing. Restore the complete source folder, including scripts. No diagnostic log could be created.', 0, 'BG3 Companion could not start', 16) | Out-Null
    exit 1
}
$log = New-CompanionLog -Project $PSScriptRoot -Purpose 'launcher'
try {
    $python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw 'The project Python environment is missing. Run setup.ps1 from this folder, then open launch.cmd again.'
    }
    $code = Invoke-CompanionPython -Executable $python -Arguments @((Join-Path $PSScriptRoot 'bg3_helper/bootstrap.py'), 'panel') -Log $log -Quiet
    if ($code -eq 20) { exit 1 } # Python already displayed a failure dialog.
    if ($code -ne 0) {
        throw 'The project Python could not start BG3 Companion. Run setup.ps1 to repair the installation, then try again.'
    }
    exit 0
} catch {
    Show-CompanionFailure -Message $_.Exception.Message -Log $log -Dialog
    exit 1
}
