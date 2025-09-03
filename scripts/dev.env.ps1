# Sets PYTHONPATH for local development (PowerShell)
$RepoRoot = Split-Path -Parent $PSScriptRoot
$paths = "${RepoRoot}\libs\sphere-core;${RepoRoot}\libs\sphere-data;${RepoRoot}\libs\sphere-flood"
[System.Environment]::SetEnvironmentVariable('PYTHONPATH', $paths, 'Process')
Write-Host "PYTHONPATH set to: $paths"
Write-Host "Run: uv run pytest -q or uv run python -c 'import sphere.core; print("OK")'"
