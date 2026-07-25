[CmdletBinding()]
param([string]$WorkDir = "")
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$head = Join-Path $repo "hls\hybrid_lif_head"
if ([string]::IsNullOrWhiteSpace($WorkDir)) { $WorkDir = Join-Path $repo "vivado\replay\replay_work" }
$WorkDir = [IO.Path]::GetFullPath($WorkDir)
$hlsWork = Join-Path $WorkDir "hls_work"
$vivadoOut = Join-Path $WorkDir "vivado"
& (Join-Path $head "scripts\run_impl_50mhz.ps1") -WorkDir $hlsWork
if ($LASTEXITCODE -ne 0) { throw "HLS implementation preparation failed" }
$rtlDir = Join-Path $hlsWork "hls\impl\verilog"
$vivado = "D:\vitis\2025.1\Vivado\bin\vivado.bat"
$settingsV = "D:\vitis\2025.1\Vivado\.settings64-Vivado.bat"
$settingsT = "D:\vitis\2025.1\Vitis\.settings64-Vitis.bat"
$tcl = Join-Path $repo "vivado\replay\tcl\run_replay_impl.tcl"
foreach ($p in @($vivado,$settingsV,$settingsT,$tcl,$rtlDir)) { if (-not (Test-Path $p)) { throw "Missing path: $p" } }
New-Item -ItemType Directory -Force -Path $vivadoOut | Out-Null
$cmd = 'call "{0}" && call "{1}" && "{2}" -mode batch -source "{3}" -tclargs "{4}" "{5}"' -f $settingsV,$settingsT,$vivado,$tcl,$rtlDir,$vivadoOut
cmd.exe /d /s /c $cmd
if ($LASTEXITCODE -ne 0) { throw "Vivado replay wrapper implementation failed" }
Write-Host "Replay wrapper implementation PASS: $vivadoOut"