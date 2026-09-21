param(
    [string]$Python,
    [switch]$IncludeTests
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
. (Join-Path $PSScriptRoot 'scripts/bootstrap.ps1')
$log = New-CompanionLog -Project $PSScriptRoot -Purpose 'setup-launcher'
# Discovery must not install a global interpreter as a side effect.
$savedAutomaticInstall = $env:PYTHON_MANAGER_AUTOMATIC_INSTALL
$savedLegacyInstall = $env:PYLAUNCHER_ALLOW_INSTALL
$env:PYTHON_MANAGER_AUTOMATIC_INSTALL = 'false'
$env:PYLAUNCHER_ALLOW_INSTALL = $null
try {
    $arguments = @()
    $environment = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if ($Python) {
        if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
            throw 'The selected Python executable does not exist. Pass its full path with -Python.'
        }
        $selected = (Resolve-Path -LiteralPath $Python).Path
        Write-Host "Using the explicitly selected Python: $selected"
    } elseif (Test-Path -LiteralPath $environment -PathType Leaf) {
        $selected = $environment
        Write-Host "Using the existing project environment: $selected"
    } elseif (Get-Command py.exe -ErrorAction SilentlyContinue) {
        $selected = (Get-Command py.exe).Source
        $arguments += '-3.14'
        Write-Host 'Selecting installed Python 3.14 with the Python launcher.'
    } else {
        $command = Get-Command python.exe -ErrorAction SilentlyContinue
        if (-not $command -or $command.Source -like '*\WindowsApps\*') {
            throw 'Python was not found. Install standard 64-bit Python 3.14 with Tcl/Tk and pip, then rerun setup.ps1 -Python with its full executable path.'
        }
        $selected = $command.Source
        Write-Host "Validating Python from PATH: $selected"
    }
    $arguments += @((Join-Path $PSScriptRoot 'bg3_helper/bootstrap.py'), 'setup')
    if ($IncludeTests) { $arguments += '--include-tests' }
    $code = Invoke-CompanionPython -Executable $selected -Arguments $arguments -Log $log
    if ($code -eq 20) { exit 1 } # Python already printed an actionable failure.
    if ($code -ne 0) {
        throw 'Python could not run setup. Install standard 64-bit Python 3.14 with Tcl/Tk and pip, or select it with -Python. See the diagnostic log.'
    }
    exit 0
} catch {
    Show-CompanionFailure -Message $_.Exception.Message -Log $log
    exit 1
} finally {
    $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = $savedAutomaticInstall
    $env:PYLAUNCHER_ALLOW_INSTALL = $savedLegacyInstall
}
