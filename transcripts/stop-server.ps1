$ErrorActionPreference = 'Stop'
$transcriptRuntime = Join-Path $PSScriptRoot 'runtime'
$transcriptPidFile = Join-Path $transcriptRuntime 'server.pid'
if (-not (Test-Path -LiteralPath $transcriptPidFile)) { exit 0 }
$transcriptManagedPid = [int](Get-Content -LiteralPath $transcriptPidFile -Raw)
$transcriptProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $transcriptManagedPid"
if ($null -eq $transcriptProcess) { exit 0 }
$transcriptExpectedExe = [System.IO.Path]::GetFullPath((Join-Path $transcriptRuntime 'ollama.exe'))
if ($transcriptProcess.ExecutablePath -ne $transcriptExpectedExe -or $transcriptProcess.CommandLine -notmatch '\bserve\b') {
    throw 'Recorded PID no longer belongs to this project writing server; nothing stopped.'
}
Stop-Process -Id $transcriptManagedPid
Write-Output 'Stopped this project writing server.'
