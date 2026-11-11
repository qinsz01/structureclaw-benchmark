# Build only in a new local directory. This script does not start Sclaw or a solver.
param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'C# compiler is unavailable; do not change the analysis interpreter to an unbuilt launcher.' }
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new output directory.' }
$destination = New-Item -ItemType Directory -Path $OutputDirectory
$executable = Join-Path $destination.FullName 'capture-worker.exe'
& $compiler /nologo /target:exe ("/out:" + $executable) (Join-Path $PSScriptRoot 'CaptureWorkerLauncher.cs')
if ($LASTEXITCODE -ne 0) { throw 'Capture launcher compilation failed.' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'capture_structureclaw_worker_v32.py') -Destination $destination.FullName
$files = @(Get-ChildItem -LiteralPath $destination.FullName -File | ForEach-Object {
    [ordered]@{ name=$_.Name; sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant() }
})
$receipt = [ordered]@{ kind='research300-capture-launcher-build'; files=$files; executionVerified=$false; deployed=$false } | ConvertTo-Json -Depth 5
[IO.File]::WriteAllText((Join-Path $destination.FullName 'launcher-build.json'), $receipt, (New-Object Text.UTF8Encoding $false))
