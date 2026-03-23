param(
  [switch]$Yes,
  [switch]$DryRun,
  [switch]$ResetProviderConnections,
  [switch]$ResetRuntimeHosts,
  [switch]$SkipBuiltinSync
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonScript = Join-Path $PSScriptRoot "reset-local-demo.py"

if (-not (Test-Path $pythonScript)) {
  throw "Reset script not found: $pythonScript"
}

$arguments = @($pythonScript)

if ($Yes) { $arguments += "--yes" }
if ($DryRun) { $arguments += "--dry-run" }
if ($ResetProviderConnections) { $arguments += "--reset-provider-connections" }
if ($ResetRuntimeHosts) { $arguments += "--reset-runtime-hosts" }
if ($SkipBuiltinSync) { $arguments += "--skip-builtin-sync" }

Push-Location $repoRoot
try {
  & python @arguments
  exit $LASTEXITCODE
}
finally {
  Pop-Location
}
