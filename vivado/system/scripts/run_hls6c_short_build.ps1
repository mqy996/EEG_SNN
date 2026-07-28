[CmdletBinding()]
param(
    [string]$WorkDir = 'D:\v6c_hls6c_20260728',
    [string]$Platform = 'p6c',
    [string]$App = 'a6c'
)
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$xsa = Join-Path $repo 'vivado\system\artifacts\smartconnect_snn_wrapper_50mhz\smartconnect_snn_wrapper_50mhz.xsa'
$source = Join-Path $repo 'vivado\system\vitis\snn_replay_standalone'
$script = Join-Path $source 'scripts\create_vitis_standalone_app.py'
$settingsVivado = 'D:\vitis\2025.1\Vivado\.settings64-Vivado.bat'
$settingsVitis = 'D:\vitis\2025.1\Vitis\.settings64-Vitis.bat'
$vitis = 'D:\vitis\2025.1\Vitis\bin\vitis.bat'
foreach($path in @($xsa,$source,$script,$settingsVivado,$settingsVitis,$vitis)) {
    if(-not (Test-Path -LiteralPath $path)) { throw "Missing path: $path" }
}
$WorkDir = [IO.Path]::GetFullPath($WorkDir)
if(Test-Path -LiteralPath $WorkDir) {
    throw "WorkDir already exists; choose a fresh short path and do not overwrite prior evidence: $WorkDir"
}
$env:SNN_REPLAY_XSA = $xsa
$env:SNN_REPLAY_WORKSPACE = $WorkDir
$env:SNN_REPLAY_SOURCE = $source
$env:SNN_REPLAY_PLATFORM = $Platform
$env:SNN_REPLAY_APP = $App
$logDir = Join-Path $repo 'vivado\system\reports'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'HLS6C_SHORT_PLATFORM_BUILD.log'
$cmd = 'call "{0}" && call "{1}" && call "{2}" -s "{3}"' -f $settingsVivado,$settingsVitis,$vitis,$script
"HLS6C short platform build" | Tee-Object -FilePath $log
"WORKSPACE=$WorkDir" | Tee-Object -FilePath $log -Append
"PLATFORM=$Platform APP=$App" | Tee-Object -FilePath $log -Append
cmd.exe /d /s /c $cmd 2>&1 | Tee-Object -FilePath $log -Append
$exitCode = $LASTEXITCODE
"VITIS_EXIT_CODE=$exitCode" | Tee-Object -FilePath $log -Append
if($exitCode -ne 0) {
    $xpfm = Join-Path $WorkDir ("{0}\export\{0}\{0}.xpfm" -f $Platform)
    $elf = Join-Path $WorkDir ("{0}\build\{0}.elf" -f $App)
    if((Test-Path -LiteralPath $xpfm) -and (Test-Path -LiteralPath $elf)) {
        "ARTIFACT_STATUS=SUCCESS despite wrapper exit code $exitCode" | Tee-Object -FilePath $log -Append
        Write-Warning "Vitis wrapper returned $exitCode after successful platform/ELF artifacts; treating artifacts as authoritative."
        exit 0
    }
    throw "Vitis HLS-6C build failed; inspect $log"
}
Write-Host "HLS6C short platform/application build completed: $WorkDir"
