param([switch]$Gpu, [switch]$Vulkan)
$ErrorActionPreference = 'Stop'
$transcriptRoot = Split-Path -Parent $PSScriptRoot
$transcriptConfig = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'config.json') -Raw | ConvertFrom-Json
try {
    $transcriptVersion = Invoke-RestMethod -Uri ($transcriptConfig.endpoint + '/api/version') -TimeoutSec 2
    Write-Output "Local writing server already available: $($transcriptVersion.version)"
    exit 0
} catch {}
$transcriptRuntime = Join-Path $PSScriptRoot 'runtime'
$transcriptExe = Join-Path $transcriptRuntime 'ollama.exe'
if (-not (Test-Path -LiteralPath $transcriptExe)) {
    throw 'Install the portable runtime first; see transcripts/README.md.'
}
$env:OLLAMA_HOST = ([uri]$transcriptConfig.endpoint).Authority
$env:OLLAMA_MODELS = Join-Path $transcriptRoot 'media/ollama-models'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_CONTEXT_LENGTH = '8192'
$env:OLLAMA_VULKAN = $(if ($Vulkan) { '1' } else { '0' })
# NVIDIA CUDA is discovered automatically when installed. Inference requests
# choose the layer count; -Gpu retains an explicit launch spelling for callers.
$transcriptProcess = Start-Process -FilePath $transcriptExe -ArgumentList 'serve' -WorkingDirectory $transcriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $transcriptRuntime 'server.stdout.log') -RedirectStandardError (Join-Path $transcriptRuntime 'server.stderr.log') -PassThru
$transcriptProcess.Id | Set-Content -LiteralPath (Join-Path $transcriptRuntime 'server.pid')
Write-Output "Started local writing server, PID $($transcriptProcess.Id)."
