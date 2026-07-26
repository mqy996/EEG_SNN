[CmdletBinding()]
param([ValidateSet("bd_only","candidate_impl","candidate_bitstream","project_impl","project_bitstream")][string]$Mode="candidate_impl", [string]$WorkDir="")
$ErrorActionPreference="Stop"
$repo=(Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
if ([string]::IsNullOrWhiteSpace($WorkDir)) { $WorkDir=Join-Path $repo "vivado\system\snn_system_work" }
$WorkDir=[IO.Path]::GetFullPath($WorkDir)
$settingsV="D:\vitis\2025.1\Vivado\.settings64-Vivado.bat"
$vivado="D:\vitis\2025.1\Vivado\bin\vivado.bat"
$tcl=Join-Path $repo "vivado\system\tcl\create_snn_replay_system.tcl"
foreach($p in @($settingsV,$vivado,$tcl)){if(-not(Test-Path $p)){throw "Missing path: $p"}}
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
$cmd='call "{0}" && call "{1}" -mode batch -source "{2}" -tclargs "{3}" "{4}" "{5}"' -f $settingsV,$vivado,$tcl,$repo,$WorkDir,$Mode
cmd.exe /d /s /c $cmd
if($LASTEXITCODE -ne 0){throw "SNN replay system failed in mode $Mode"}
Write-Host "SNN replay system PASS: $Mode -> $WorkDir"
