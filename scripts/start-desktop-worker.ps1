param(
    [string]$ApiBaseUrl = "http://localhost:8000",
    [string]$RuntimeSharedToken = "dreamaxis-runtime-token",
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8300,
    [string]$PublicUrl = "",
    [string]$RuntimeId = "runtime-desktop-host-local",
    [string]$RuntimeName = "Host Desktop Runtime",
    [string]$ScopeType = "machine",
    [string]$ScopeRefId = "host-local",
    [string]$AccessMode = "host",
    [string]$RepoRoot = "",
    [switch]$InstallDeps,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$workerDir = Join-Path $repoRoot "apps\\desktop-worker"

if (-not $PublicUrl) {
    $PublicUrl = "http://host.docker.internal:$Port"
}

if ($InstallDeps) {
    Write-Host "Installing desktop worker dependencies from $workerDir ..."
    python -m pip install -e $workerDir
}

$env:API_BASE_URL = $ApiBaseUrl
$env:RUNTIME_SHARED_TOKEN = $RuntimeSharedToken
$env:DESKTOP_WORKER_PUBLIC_URL = $PublicUrl
$env:DESKTOP_WORKER_RUNTIME_ID = $RuntimeId
$env:DESKTOP_WORKER_NAME = $RuntimeName
$env:DESKTOP_WORKER_SCOPE_TYPE = $ScopeType
$env:DESKTOP_WORKER_SCOPE_REF_ID = $ScopeRefId
$env:DESKTOP_WORKER_ACCESS_MODE = $AccessMode

if ($RepoRoot) {
    $env:DESKTOP_WORKER_REPO_ROOT = $RepoRoot
}

$uvicornArgs = @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", $BindHost,
    "--port", "$Port"
)

if ($Reload) {
    $uvicornArgs += "--reload"
}

Write-Host "Starting DreamAxis desktop worker"
Write-Host "  worker dir  : $workerDir"
Write-Host "  API base    : $ApiBaseUrl"
Write-Host "  public url  : $PublicUrl"
Write-Host "  runtime id  : $RuntimeId"
Write-Host "  scope       : $ScopeType/$ScopeRefId"
Write-Host "  access mode : $AccessMode"
if ($RepoRoot) {
    Write-Host "  repo root   : $RepoRoot"
}

Push-Location $workerDir
try {
    & python @uvicornArgs
}
finally {
    Pop-Location
}
