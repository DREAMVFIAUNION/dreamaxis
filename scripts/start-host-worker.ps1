param(
    [string]$ApiBaseUrl = "http://localhost:8000",
    [string]$RuntimeSharedToken = "dreamaxis-runtime-token",
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8110,
    [string]$PublicUrl = "",
    [string]$RuntimeId = "runtime-cli-host-local",
    [string]$RuntimeName = "Host CLI Runtime",
    [string]$ScopeType = "machine",
    [string]$ScopeRefId = "host-local",
    [string]$RepoRoot = "",
    [string]$Shell = "powershell",
    [switch]$InstallDeps,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$workerDir = Join-Path $repoRoot "apps\\worker"

if (-not $PublicUrl) {
    $PublicUrl = "http://host.docker.internal:$Port"
}

if ($InstallDeps) {
    Write-Host "Installing host worker dependencies from $workerDir ..."
    python -m pip install -e $workerDir
}

$env:API_BASE_URL = $ApiBaseUrl
$env:RUNTIME_SHARED_TOKEN = $RuntimeSharedToken
$env:WORKER_HOST = $BindHost
$env:WORKER_PORT = "$Port"
$env:WORKER_PUBLIC_URL = $PublicUrl
$env:WORKER_RUNTIME_ID = $RuntimeId
$env:WORKER_NAME = $RuntimeName
$env:WORKER_SCOPE_TYPE = $ScopeType
$env:WORKER_SCOPE_REF_ID = $ScopeRefId
$env:WORKER_SHELL = $Shell
$env:WORKER_ACCESS_MODE = "host"

if ($RepoRoot) {
    $env:WORKER_REPO_ROOT = $RepoRoot
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

Write-Host "Starting DreamAxis host worker"
Write-Host "  worker dir  : $workerDir"
Write-Host "  API base    : $ApiBaseUrl"
Write-Host "  public url  : $PublicUrl"
Write-Host "  runtime id  : $RuntimeId"
Write-Host "  scope       : $ScopeType/$ScopeRefId"
Write-Host "  access mode : host"

Push-Location $workerDir
try {
    & python @uvicornArgs
}
finally {
    Pop-Location
}
