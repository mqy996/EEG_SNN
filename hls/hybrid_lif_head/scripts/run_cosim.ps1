$ErrorActionPreference = "Stop"

$headDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
# Vitis 2025.1 resolves the component work directory from the HLS head
# when running `vitis-run`; keep compile and cosim in the same head dir.
$WorkDir = $headDir

$vivadoSettings = "D:\vitis\2025.1\Vivado\.settings64-Vivado.bat"
$vitisSettings = "D:\vitis\2025.1\Vitis\.settings64-Vitis.bat"
$vitisCompiler = "D:\vitis\2025.1\Vitis\bin\v++.bat"
$vitisRun = "D:\vitis\2025.1\Vitis\bin\vitis-run.bat"
$config = Join-Path $headDir "config\hls_cosim_config.cfg"
$source = Join-Path $headDir "src\hybrid_lif_head.cpp"
$logDir = Join-Path $headDir "logs"
$compileLog = Join-Path $logDir "hls_run_cosim_compile.log"
$runStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$consoleLog = Join-Path $logDir ("run_cosim_console_{0}.log" -f $runStamp)
$part = "xc7z020clg400-1"

foreach ($path in @($vivadoSettings, $vitisSettings, $vitisCompiler, $vitisRun, $config, $source)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required Vitis/HLS path does not exist: $path"
    }
}

$workParent = Split-Path -Parent $WorkDir
New-Item -ItemType Directory -Force -Path $workParent | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# The cosim testbench is intentionally part of a separate config. This first
# compile creates a solution whose testbench matches the RTL run; relying on a
# stale HLS-3 work directory can produce COSIM-5 file-generation failures.
$compileCommand = 'call "{0}" && call "{1}" && "{2}" -c --mode hls --part "{3}" --config "{4}" "{5}" --work_dir "{6}"' -f `
    $vivadoSettings, $vitisSettings, $vitisCompiler, $part, $config, $source, $WorkDir
Write-Host "Preparing matching HLS solution for C/RTL co-simulation"
Write-Host "  Compile command: $compileCommand"
cmd.exe /d /s /c ('{0} > "{1}" 2>&1' -f $compileCommand, $compileLog)
$compileExitCode = $LASTEXITCODE
if ($compileExitCode -ne 0) {
    Get-Content -LiteralPath $compileLog | Write-Host
    throw "HLS cosim preparation failed with exit code $compileExitCode. See $compileLog"
}

$cosimCommand = 'call "{0}" && call "{1}" && "{2}" --mode hls --cosim --config "{3}" --work_dir "{4}"' -f `
    $vivadoSettings, $vitisSettings, $vitisRun, $config, $WorkDir
Write-Host "Running Vitis HLS C/RTL co-simulation"
Write-Host "  Config:   $config"
Write-Host "  Work dir: $WorkDir"
Write-Host "  Cosim command: $cosimCommand"
cmd.exe /d /s /c ('{0} > "{1}" 2>&1' -f $cosimCommand, $consoleLog)
$exitCode = $LASTEXITCODE

$output = if (Test-Path -LiteralPath $consoleLog) {
    Get-Content -LiteralPath $consoleLog
} else {
    @()
}
$output | Write-Host

if ($exitCode -ne 0) {
    throw "Vitis HLS C/RTL co-simulation failed with exit code $exitCode. See $consoleLog"
}

$passLine = $output | Where-Object { $_ -match 'HLS-4 C/RTL co-simulation PASS cases=3' }
$cosimLine = $output | Where-Object { $_ -match 'C/RTL co-simulation finished: PASS' }
if (-not $passLine) {
    throw "Co-simulation command succeeded but the testbench PASS case summary was not found. See $consoleLog"
}
if (-not $cosimLine) {
    throw "Co-simulation command succeeded but the Vitis C/RTL completion marker was not found. See $consoleLog"
}

Write-Host "Vitis HLS C/RTL co-simulation PASS: $passLine"
Write-Host "Vitis completion marker: $cosimLine"
Write-Host "Full log: $consoleLog"
