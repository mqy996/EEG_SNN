[CmdletBinding()]
param(
  [string]$WorkRoot = ""
)
$ErrorActionPreference = "Stop"
$head = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($WorkRoot)) { $WorkRoot = Join-Path $head "board_target_50mhz_work" }
$WorkRoot = [IO.Path]::GetFullPath($WorkRoot)
$vivado = "D:\vitis\2025.1\Vivado\.settings64-Vivado.bat"
$vitis = "D:\vitis\2025.1\Vitis\.settings64-Vitis.bat"
$vpp = "D:\vitis\2025.1\Vitis\bin\v++.bat"
$vitisRun = "D:\vitis\2025.1\Vitis\bin\vitis-run.bat"
$source = Join-Path $head "src\hybrid_lif_head.cpp"
$configDir = Join-Path $head "config"
$csimCfg = Join-Path $configDir "hls_board_50mhz_csim.cfg"
$cosimCfg = Join-Path $configDir "hls_board_50mhz_cosim.cfg"
$implCfg = Join-Path $configDir "hls_board_50mhz_impl.cfg"
$logDir = Join-Path $WorkRoot "logs"
New-Item -ItemType Directory -Force -Path $WorkRoot,$logDir | Out-Null
foreach ($p in @($vivado,$vitis,$vpp,$vitisRun,$source,$csimCfg,$cosimCfg,$implCfg)) { if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "Missing required path: $p" } }
function Run-Cmd([string]$name,[string]$command,[string]$log) {
  Write-Host "=== $name ==="
  Write-Host $command
  cmd.exe /d /s /c ('{0} > "{1}" 2>&1' -f $command,$log)
  $code=$LASTEXITCODE
  if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log | Write-Host }
  if ($code -ne 0) { throw "$name failed with exit code $code. See $log" }
}
Run-Cmd "HLS-6A C simulation" ('call "{0}" && call "{1}" && "{2}" --mode hls --csim --config "{3}" --work_dir "{4}"' -f $vivado,$vitis,$vitisRun,$csimCfg,(Join-Path $WorkRoot "csim")) (Join-Path $logDir "csim.log")
$csimText=Get-Content -Raw (Join-Path $logDir "csim.log")
if ($csimText -notmatch 'HLS-2 C simulation PASS cases=3') { throw 'HLS-2 PASS marker missing' }
Run-Cmd "HLS-6A C/RTL co-simulation compile" ('call "{0}" && call "{1}" && "{2}" -c --mode hls --part xc7z020clg400-2 --config "{3}" "{4}" --work_dir "{5}"' -f $vivado,$vitis,$vpp,$cosimCfg,$source,(Join-Path $WorkRoot "cosim")) (Join-Path $logDir "cosim_compile.log")
Run-Cmd "HLS-6A C/RTL co-simulation" ('call "{0}" && call "{1}" && "{2}" --mode hls --cosim --config "{3}" --work_dir "{4}"' -f $vivado,$vitis,$vitisRun,$cosimCfg,(Join-Path $WorkRoot "cosim")) (Join-Path $logDir "cosim.log")
$cosimText=Get-Content -Raw (Join-Path $logDir "cosim.log")
if ($cosimText -notmatch 'HLS-4 C/RTL co-simulation PASS cases=3') { throw 'HLS-4 PASS marker missing' }
Run-Cmd "HLS-6A implementation compile" ('call "{0}" && call "{1}" && "{2}" -c --mode hls --part xc7z020clg400-2 --config "{3}" "{4}" --work_dir "{5}"' -f $vivado,$vitis,$vpp,$implCfg,$source,(Join-Path $WorkRoot "impl")) (Join-Path $logDir "impl_compile.log")
Run-Cmd "HLS-6A 50 MHz implementation" ('call "{0}" && call "{1}" && "{2}" --mode hls --impl --config "{3}" --work_dir "{4}"' -f $vivado,$vitis,$vitisRun,$implCfg,(Join-Path $WorkRoot "impl")) (Join-Path $logDir "impl.log")
$report=Join-Path $WorkRoot "impl\hls\impl\report\verilog\hybrid_lif_head_q12_6_export.rpt"
if (-not (Test-Path -LiteralPath $report -PathType Leaf)) { throw "Implementation report missing: $report" }
Write-Host "HLS-6A PASS: target=xc7z020clg400-2 clock=20ns report=$report"
