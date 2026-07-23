[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$headDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vivadoSettings = "D:\vitis\2025.1\Vivado\.settings64-Vivado.bat"
$vitisSettings = "D:\vitis\2025.1\Vitis\.settings64-Vitis.bat"
$vitisCompiler = "D:\vitis\2025.1\Vitis\bin\v++.bat"
$config = Join-Path $headDir "config\hls_config.cfg"
$source = Join-Path $headDir "src\hybrid_lif_head.cpp"
$logDir = Join-Path $headDir "logs"
$logPath = Join-Path $logDir "hls_run_csynth.log"
$part = "xc7z020clg400-1"

foreach ($path in @($vivadoSettings, $vitisSettings, $vitisCompiler, $config, $source)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required Vitis/HLS path does not exist: $path"
    }
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# Vitis 2025.1 does not expose --csynth in vitis-run. The supported HLS
# synthesis entry is the v++ compile flow in HLS mode; it still consumes the
# HLS config and emits the standard csynth reports below the work directory.
$command = 'call "{0}" && call "{1}" && "{2}" -c --mode hls --part "{3}" --config "{4}" "{5}" --work_dir "{6}"' -f `
    $vivadoSettings, $vitisSettings, $vitisCompiler, $part, $config, $source, $headDir
$redirectedCommand = '{0} > "{1}" 2>&1' -f $command, $logPath

Write-Host "Running Vitis HLS csynth through v++ in $headDir"
Write-Host "Command: $command"

cmd.exe /d /s /c $redirectedCommand
$exitCode = $LASTEXITCODE

if (Test-Path -LiteralPath $logPath) {
    Get-Content -LiteralPath $logPath | Write-Host
}

if ($exitCode -ne 0) {
    throw "Vitis HLS csynth failed with exit code $exitCode. See $logPath"
}

Write-Host "Vitis HLS csynth completed successfully. Log: $logPath"
