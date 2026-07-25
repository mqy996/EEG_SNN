[CmdletBinding()]
param([string]$WorkDir = "")
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$head = Join-Path $repo "hls\hybrid_lif_head"
if ([string]::IsNullOrWhiteSpace($WorkDir)) { $WorkDir = Join-Path $repo "vivado\system\sim_work" }
$WorkDir = [IO.Path]::GetFullPath($WorkDir)
$hlsWork = Join-Path $WorkDir "hls_work"
$simOut = Join-Path $WorkDir "sim"
$vectorOut = Join-Path $simOut "vivado\replay\vectors"
$vectorIn = Join-Path $repo "vivado\replay\vectors"
$rtlDir = Join-Path $head "hls\impl\verilog"
$settingsV = "D:\vitis\2025.1\Vivado\.settings64-Vivado.bat"
$settingsT = "D:\vitis\2025.1\Vitis\.settings64-Vitis.bat"
$wrapper = Join-Path $repo "vivado\system\src\snn_axi_memory_window.v"
$tb = Join-Path $repo "vivado\system\tb\tb_snn_axi_memory_window.sv"
foreach ($path in @($settingsV,$settingsT,$wrapper,$tb,$rtlDir)) { if (-not (Test-Path $path)) { throw "Missing path: $path" } }
New-Item -ItemType Directory -Force -Path $simOut | Out-Null
New-Item -ItemType Directory -Force -Path $vectorOut | Out-Null
Get-ChildItem -LiteralPath $vectorIn -Filter "threshold_edge_*.mem" -File | Copy-Item -Destination $vectorOut -Force
$files = (Get-ChildItem -LiteralPath $rtlDir -Filter *.v -File | ForEach-Object { '"{0}"' -f $_.FullName }) -join ' '
$cmd = 'call "{0}" && call "{1}" && cd /d "{2}" && call xvlog -sv -work work {3} "{4}" "{5}" && call xelab -debug typical work.tb_snn_axi_memory_window -s axi_window_sim && call xsim axi_window_sim -runall' -f $settingsV,$settingsT,$simOut,$files,$wrapper,$tb
cmd.exe /d /s /c $cmd
if ($LASTEXITCODE -ne 0) { throw "AXI memory-window simulation failed" }
Write-Host "AXI memory-window simulation PASS: $simOut"
