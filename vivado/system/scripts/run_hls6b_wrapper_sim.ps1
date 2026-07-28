[CmdletBinding()]
param([string]$WorkDir = "")
$ErrorActionPreference="Stop"
$repo=(Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$hls=Join-Path $repo "vivado\system\hls_rtl\board_target_50mhz"
$wrapper=Join-Path $repo "vivado\system\src\snn_axi_memory_window_hls6a.v"
$tb=Join-Path $repo "vivado\system\tb\tb_snn_axi_memory_window_hls6a.sv"
$settingsV="D:\vitis\2025.1\Vivado\.settings64-Vivado.bat"; $settingsT="D:\vitis\2025.1\Vitis\.settings64-Vitis.bat"
if([string]::IsNullOrWhiteSpace($WorkDir)){ $WorkDir=Join-Path $repo "vivado\system\hls6b_sim_work" }
$WorkDir=[IO.Path]::GetFullPath($WorkDir); New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
$vectorSrc=Join-Path $repo "vivado\system\vectors"
$vectorDst=Join-Path $WorkDir "vivado\system\vectors"
foreach($p in @($settingsV,$settingsT,$hls,$wrapper,$tb,$vectorSrc)){if(-not(Test-Path $p)){throw "Missing path: $p"}}
New-Item -ItemType Directory -Force -Path $vectorDst | Out-Null
Get-ChildItem -LiteralPath $vectorSrc -Filter *.mem -File | Copy-Item -Destination $vectorDst -Force
$files=(Get-ChildItem -LiteralPath $hls -Filter *.v -File | ForEach-Object { '"{0}"' -f $_.FullName }) -join ' '
$cmd='call "{0}" && call "{1}" && cd /d "{2}" && call xvlog -sv -work work {3} "{4}" "{5}" && call xelab -debug typical work.tb_snn_axi_memory_window_hls6a -s hls6b_wrapper_sim && call xsim hls6b_wrapper_sim -runall' -f $settingsV,$settingsT,$WorkDir,$files,$wrapper,$tb
cmd.exe /d /s /c $cmd
if($LASTEXITCODE -ne 0){throw "HLS-6B wrapper simulation failed"}
Write-Host "HLS-6B wrapper simulation PASS: $WorkDir"
