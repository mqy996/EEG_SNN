[CmdletBinding()]
param(
    [string]$WorkDir = "",
    [string]$ReportPath = ""
)

$ErrorActionPreference = 'Stop'
$systemRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$wrapper = Join-Path $systemRoot 'src\snn_axi_memory_window_hls6a.v'
$tb = Join-Path $systemRoot 'tb\tb_snn_axi_version_read_hls6d.sv'
$settingsVivado = 'D:\vitis\2025.1\Vivado\.settings64-Vivado.bat'

if ([string]::IsNullOrWhiteSpace($WorkDir)) {
    $WorkDir = Join-Path $systemRoot 'hls6d_axi_lite_version_sim_work'
}
if ([string]::IsNullOrWhiteSpace($ReportPath)) {
    $ReportPath = Join-Path $systemRoot 'reports\HLS6D_AXI_LITE_VERSION_SIM.log'
}
$WorkDir = [IO.Path]::GetFullPath($WorkDir)
$ReportPath = [IO.Path]::GetFullPath($ReportPath)

foreach ($path in @($wrapper, $tb, $settingsVivado)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing required path: $path" }
}
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ReportPath) | Out-Null

$start = Get-Date -Format 'yyyy-MM-dd HH:mm:ss K'
@(
    'HLS-6D focused AXI4-Lite VERSION/STATUS simulation',
    "START=$start",
    "WRAPPER=$wrapper",
    "TESTBENCH=$tb",
    "WORKDIR=$WorkDir",
    'SCOPE=wrapper AR/R channel only; generated HLS core is stubbed by the testbench',
    'EXPECTATION=AR handshake -> registered RVALID/RDATA within one clock; VERSION=0x00010001; RVALID stable until RREADY'
) | Set-Content -LiteralPath $ReportPath -Encoding utf8

$cmd = 'call "{0}" && cd /d "{1}" && call xvlog -sv -work work "{2}" "{3}" && call xelab -debug typical work.tb_snn_axi_version_read_hls6d -s hls6d_axi_version_sim && call xsim hls6d_axi_version_sim -runall' -f $settingsVivado, $WorkDir, $wrapper, $tb
$toolOutput = cmd.exe /d /s /c $cmd 2>&1
$exitCode = $LASTEXITCODE
$toolOutput | Write-Output
"SIM_EXIT_CODE=$exitCode" | Add-Content -LiteralPath $ReportPath -Encoding utf8

if ($exitCode -ne 0) { throw "HLS-6D AXI-Lite VERSION simulation failed; inspect $ReportPath" }
$xsimLog = Join-Path $WorkDir 'xsim.log'
if (-not (Test-Path -LiteralPath $xsimLog)) {
    throw "HLS-6D AXI-Lite VERSION simulation did not produce xsim.log: $xsimLog"
}
if (-not (Select-String -LiteralPath $xsimLog -SimpleMatch 'HLS6D_AXI_VERSION_SIM_PASS' -Quiet)) {
    throw "HLS-6D AXI-Lite VERSION simulation did not emit its PASS marker; inspect $xsimLog"
}
"XSIM_LOG=$xsimLog" | Add-Content -LiteralPath $ReportPath -Encoding utf8
'--- XSIM EVIDENCE ---' | Add-Content -LiteralPath $ReportPath -Encoding utf8
Get-Content -LiteralPath $xsimLog | Where-Object { $_ -match 'HLS6D_|ERROR:|FATAL:' } | Add-Content -LiteralPath $ReportPath -Encoding utf8

$vcd = Join-Path $WorkDir 'hls6d_axi_lite_version.vcd'
if (Test-Path -LiteralPath $vcd) {
    "WAVEFORM=$vcd" | Add-Content -LiteralPath $ReportPath -Encoding utf8
} else {
    "WAVEFORM=not-produced-by-xsim" | Add-Content -LiteralPath $ReportPath -Encoding utf8
}
Write-Host "HLS-6D AXI-Lite VERSION simulation PASS: $ReportPath"
