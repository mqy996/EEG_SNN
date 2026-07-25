[CmdletBinding()]
param(
    [string]$WorkDir = ""
)

$ErrorActionPreference = "Stop"
$headDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($WorkDir)) {
    $WorkDir = Join-Path $headDir "impl_50mhz_work"
}
$WorkDir = [IO.Path]::GetFullPath($WorkDir)
$vivadoSettings = "D:\vitis\2025.1\Vivado\.settings64-Vivado.bat"
$vitisSettings = "D:\vitis\2025.1\Vitis\.settings64-Vitis.bat"
$vitisCompiler = "D:\vitis\2025.1\Vitis\bin\v++.bat"
$vitisRun = "D:\vitis\2025.1\Vitis\bin\vitis-run.bat"
$config = Join-Path $headDir "config\hls_impl_50mhz.cfg"
$source = Join-Path $headDir "src\hybrid_lif_head.cpp"
$logDir = Join-Path $headDir "logs"
$compileLog = Join-Path $logDir "hls_run_impl_50mhz_compile.log"
$implLog = Join-Path $logDir "hls_run_impl_50mhz.log"
$part = "xc7z020clg400-1"

foreach ($path in @($vivadoSettings, $vitisSettings, $vitisCompiler, $vitisRun, $config, $source)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required Vitis/HLS path does not exist: $path"
    }
}
New-Item -ItemType Directory -Force -Path $logDir, $WorkDir | Out-Null

$compileCommand = 'call "{0}" && call "{1}" && "{2}" -c --mode hls --part "{3}" --config "{4}" --work_dir "{5}"' -f `
    $vivadoSettings, $vitisSettings, $vitisCompiler, $part, $config, $WorkDir
Write-Host "Preparing 50 MHz HLS implementation in $WorkDir"
cmd.exe /d /s /c ('{0} > "{1}" 2>&1' -f $compileCommand, $compileLog)
if ($LASTEXITCODE -ne 0) {
    Get-Content -LiteralPath $compileLog | Write-Host
    throw "50 MHz HLS preparation failed. See $compileLog"
}

$implCommand = 'call "{0}" && call "{1}" && "{2}" --mode hls --impl --config "{3}" --work_dir "{4}"' -f `
    $vivadoSettings, $vitisSettings, $vitisRun, $config, $WorkDir
Write-Host "Running Vivado out-of-context implementation at 50 MHz"
cmd.exe /d /s /c ('{0} > "{1}" 2>&1' -f $implCommand, $implLog)
Get-Content -LiteralPath $implLog | Write-Host
if ($LASTEXITCODE -ne 0) {
    throw "50 MHz HLS/Vivado implementation failed. See $implLog"
}

$report = Join-Path $WorkDir "hls\impl\report\verilog\hybrid_lif_head_q12_6_export.rpt"
if (-not (Test-Path -LiteralPath $report -PathType Leaf)) {
    throw "Implementation completed without the expected report: $report"
}
Write-Host "50 MHz HLS/Vivado implementation PASS"
Write-Host "Report: $report"