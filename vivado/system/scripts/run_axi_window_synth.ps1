[CmdletBinding()]
param([string]$WorkDir = "")
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$head = Join-Path $repo "hls\hybrid_lif_head"
if ([string]::IsNullOrWhiteSpace($WorkDir)) { $WorkDir = Join-Path $repo "vivado\system\synth_work" }
$WorkDir = [IO.Path]::GetFullPath($WorkDir)
$rtlDir = Join-Path $head "hls\impl\verilog"
$outDir = Join-Path $WorkDir "reports"
$settingsV = "D:\vitis\2025.1\Vivado\.settings64-Vivado.bat"
$vivado = "D:\vitis\2025.1\Vivado\bin\vivado.bat"
$tcl = Join-Path $repo "vivado\system\tcl\run_axi_window_synth.tcl"
foreach ($path in @($settingsV,$vivado,$tcl,$rtlDir)) { if (-not (Test-Path $path)) { throw "Missing path: $path" } }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$cmd = 'call "{0}" && call "{1}" -mode batch -source "{2}" -tclargs "{3}" "{4}"' -f $settingsV,$vivado,$tcl,$rtlDir,$outDir
cmd.exe /d /s /c $cmd
if ($LASTEXITCODE -ne 0) { throw "AXI memory-window synthesis failed" }
Write-Host "AXI memory-window synthesis PASS: $outDir"
