$ErrorActionPreference = "Stop"

$headDir = (Resolve-Path (Join-Path $PSScriptRoot ".."))
$packageRoot = (Resolve-Path (Join-Path $headDir "..\.."))
$vivadoSettings = "D:\vitis\2025.1\Vivado\.settings64-Vivado.bat"
$vitisSettings = "D:\vitis\2025.1\Vitis\.settings64-Vitis.bat"
$vitisRun = "D:\vitis\2025.1\Vitis\bin\vitis-run.bat"
$config = Join-Path $headDir "config\hls_config.cfg"

foreach ($path in @($vivadoSettings, $vitisSettings, $vitisRun, $config)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required Vitis/HLS path does not exist: $path"
    }
}

$command = 'call "{0}" && call "{1}" && "{2}" --mode hls --csim --config "{3}" --work_dir "{4}"' -f `
    $vivadoSettings, $vitisSettings, $vitisRun, $config, $headDir
Write-Host "Running Vitis HLS csim in $headDir"
cmd.exe /d /s /c $command
if ($LASTEXITCODE -ne 0) {
    throw "Vitis HLS csim failed with exit code $LASTEXITCODE"
}
