[CmdletBinding()]
param([string]$WorkDir = "")
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$head = Join-Path $repo "hls\hybrid_lif_head"
if ([string]::IsNullOrWhiteSpace($WorkDir)) { $WorkDir = Join-Path $repo "vivado\replay\sim_work" }
$WorkDir = [IO.Path]::GetFullPath($WorkDir)
$hlsWork = Join-Path $WorkDir "hls_work"
$simOut = Join-Path $WorkDir "sim"
& (Join-Path $head "scripts\run_impl_50mhz.ps1") -WorkDir $hlsWork
if ($LASTEXITCODE -ne 0) { throw "HLS implementation preparation failed" }
$rtlDir = Join-Path $hlsWork "hls\impl\verilog"
$settingsV = "D:\vitis\2025.1\Vivado\.settings64-Vivado.bat"
$settingsT = "D:\vitis\2025.1\Vitis\.settings64-Vitis.bat"
$tb = Join-Path $repo "vivado\replay\tb\tb_hls_replay_wrapper.sv"
$wrapper = Join-Path $repo "vivado\replay\src\hls_replay_wrapper.v"
foreach ($p in @($settingsV,$settingsT,$tb,$wrapper,$rtlDir)) { if (-not (Test-Path $p)) { throw "Missing path: $p" } }
New-Item -ItemType Directory -Force -Path $simOut | Out-Null
$files = (Get-ChildItem -LiteralPath $rtlDir -Filter *.v -File | ForEach-Object { '"{0}"' -f $_.FullName }) -join ' '
$cmd = 'call "{0}" && call "{1}" && cd /d "{2}" && call xvlog -sv -work work {3} "{4}" "{5}" && call xelab -debug typical work.tb_hls_replay_wrapper -s replay_sim && call xsim replay_sim -runall' -f $settingsV,$settingsT,$simOut,$files,$wrapper,$tb
cmd.exe /d /s /c $cmd
if ($LASTEXITCODE -ne 0) { throw "Replay wrapper simulation failed" }
Write-Host "Replay wrapper simulation PASS: $simOut"
