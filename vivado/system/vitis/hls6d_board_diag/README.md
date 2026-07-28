# HLS-6D board diagnostic standalone app

This app is intentionally narrower than HLS-6C replay. It performs only these
operations, in this order:

1. Print `HLS6D_DIAG_START`.
2. Read AXI GPIO at `0x41200000` and print the result.
3. Read SNN `VERSION` at `0x43C00008` and print the result.
4. If execution returns from that read, read SNN `STATUS` at `0x43C00004`.
5. Print `HLS6D_DIAG_COMPLETE` and exit.

It does not write SNN control, feature, weight, bias, or index registers and it
does not run golden replay. The existing HLS-6B bitstream is used unchanged.

## Build

Use Vitis 2025.1 with a new short workspace. The build script requires:

```powershell
$env:HLS6D_DIAG_XSA = (Resolve-Path ..\..\artifacts\smartconnect_snn_wrapper_50mhz\smartconnect_snn_wrapper_50mhz.xsa).Path
$env:HLS6D_DIAG_BITSTREAM = (Resolve-Path ..\..\artifacts\smartconnect_snn_wrapper_50mhz\smartconnect_snn_wrapper_50mhz.bit).Path
$env:HLS6D_DIAG_WORKSPACE = 'D:/v6d_hls6d_20260728'
$env:HLS6D_DIAG_SOURCE = (Resolve-Path .).Path
$env:HLS6D_DIAG_ARTIFACT_DIR = (Resolve-Path ..\..\artifacts\smartconnect_snn_wrapper_50mhz\hls6d_board_diag).Path
& 'D:/vitis/2025.1/Vitis/bin/vitis.bat' -s scripts/create_vitis_standalone_app.py
```

The script uses unique component names `hls6d_diag_platform_20260728` and
`hls6d_diag_app_20260728`, verifies `.buildstatus`, and writes a SHA-256
manifest covering the XSA, unchanged HLS-6B bitstream, copied XPFM, and copied
ELF to the curated artifact directory when `HLS6D_DIAG_ARTIFACT_DIR` is
provided.

## Board order

Program the existing HLS-6B bitstream, download the generated diagnostic ELF,
and capture COM5 at 115200 8-N-1. The capture helper has a global timeout and
stops at the first missing marker. Do not run full replay or ILA as part of
HLS-6D.
