# Shared dependency-free reporting for failures before Python can start.
function New-CompanionLog {
    param([string]$Project, [string]$Purpose)
    $name = '{0}-{1}-{2}.log' -f $Purpose, (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0, 8))
    foreach ($directory in @((Join-Path $Project '.runtime/logs'), (Join-Path ([IO.Path]::GetTempPath()) 'BG3Companion'))) {
        try {
            [IO.Directory]::CreateDirectory($directory) | Out-Null
            $path = Join-Path $directory $name
            [IO.File]::WriteAllText($path, "BG3 Companion $Purpose`r`n")
            return $path
        } catch { }
    }
    return $null
}

function Show-CompanionFailure {
    param([string]$Message, [string]$Log, [switch]$Dialog)
    if ($Log) {
        try { [IO.File]::AppendAllText($Log, "$Message`r`n") } catch { }
        $Message += "`n`nDiagnostic log: $Log"
    } else {
        $Message += "`n`nNo log could be written. Check project and temporary-folder write access."
    }
    if ($Dialog) {
        $shell = New-Object -ComObject WScript.Shell
        $shell.Popup($Message, 0, 'BG3 Companion could not start', 16) | Out-Null
    } else {
        [Console]::Error.WriteLine($Message)
    }
}

function Invoke-CompanionPython {
    param([string]$Executable, [string[]]$Arguments, [string]$Log, [switch]$Quiet)
    # Windows PowerShell 5 wraps native stderr in ErrorRecord. Judge exit status.
    $savedPreference = $ErrorActionPreference
    $savedEncoding = [Console]::OutputEncoding
    $savedPythonEncoding = $env:PYTHONIOENCODING
    $savedPythonUtf8 = $env:PYTHONUTF8
    $ErrorActionPreference = 'Continue'
    try {
        [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
        $env:PYTHONIOENCODING = 'utf-8'
        $env:PYTHONUTF8 = '1'
        # Native commands update the global automatic variable, even in a function.
        $global:LASTEXITCODE = -1
        & $Executable @Arguments 2>&1 | ForEach-Object {
            if ($Log) { [IO.File]::AppendAllText($Log, "$_`r`n") }
            if (-not $Quiet) { Write-Host $_ }
        }
        return $global:LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedPreference
        [Console]::OutputEncoding = $savedEncoding
        $env:PYTHONIOENCODING = $savedPythonEncoding
        $env:PYTHONUTF8 = $savedPythonUtf8
    }
}
