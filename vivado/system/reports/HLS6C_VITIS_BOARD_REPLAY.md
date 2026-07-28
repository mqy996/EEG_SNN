# HLS-6C Vitis standalone / AXI-Lite board replay report

**Result: BLOCKED at Vitis platform/BSP build gate — no board replay was attempted.**

Date: **2026-07-28**

Tool environment: **Vitis 2025.1, SW Build 6137779 (2025-05-21-18:10:19)**

Scope: HLS-6B SmartConnect SNN wrapper only; HLS-6B artifacts were not modified.

## 1. Evidence ladder and claim boundary

| Level | Result | Evidence |
|---|---|---|
| HLS-6B implementation input | AVAILABLE | XSA/bitstream/HWH under `vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/` |
| Vitis platform/domain | **BLOCKED** | Two fresh platform workspaces ended with `export=ERROR`; no `.xpfm` |
| Standalone application / ELF | NOT REACHED | Platform stop gate; no application build started successfully |
| Bitstream download | NOT ATTEMPTED | No valid HLS-6C platform/ELF evidence |
| UART smoke / AXI first transaction | NOT ATTEMPTED | No ELF to run |
| Three-case board replay | NOT ATTEMPTED | No board claim is made |

A successful HLS-6B Vivado implementation, a Vitis process exit code, or source-code PASS strings are not treated as board evidence.

## 2. HLS-6B input identity

| Artifact | Path | SHA-256 |
|---|---|---|
| XSA | `vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/smartconnect_snn_wrapper_50mhz.xsa` | `373543b2a9a283339f3d48bcd20cb38cc299a0f416faae84ba3b0dcc303ba98b` |
| bitstream | `vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/smartconnect_snn_wrapper_50mhz.bit` | `d5e90c144c02dddf4af94ec85208dfd285b2f672ee13bb18ca7c18b4950bab8d` |
| HWH | `vivado/system/artifacts/smartconnect_snn_wrapper_50mhz/smartconnect_snn_wrapper_50mhz.hwh` | `8c5f1d0c93dc8141e1d985c8f4d42f6dc5bda2ab69d871b31ff3d3566b9c521d` |

The XSA `sysdef.xml` identifies `xc7z020clg400-2`. The packaged HWH/XSA metadata was checked for the documented PS7 contract: FCLK0/GP0 at 50 MHz, UART1 at 115200 on MIO48/49, DDR `MT41J256M16 RE-125`, SNN wrapper `0x43C00000`, and AXI GPIO `0x41200000`.

Golden input identity:

- manifest: `vivado/system/vitis/snn_replay_standalone/include/golden_vectors_manifest.json`
- SHA-256: `8f73683b4448f8315af76151e36dacff494197c0caf8bcf2e8ace01ad301604a`
- cases: `threshold_edge, signed_currents, rounding_and_reset`
- schema: `hls-q12.6-golden-v1`
- generated header: `include/golden_vectors_q12_6.h`

The checked golden JSON hash matches the manifest/header contract. No golden vectors or HLS-6B artifacts were changed.

## 3. Source/script changes made before the stop gate

- `src/main.c`
  - emits `SNN standalone replay start` before the first AXI read;
  - emits a `VERSION_BEGIN` marker before reading `VERSION`;
  - preserves the required sequence VERSION → soft reset → indexed feature/weight/bias writes → checksum → START → DONE polling → error/status/output comparison;
  - logs reset status, first feature write, checksum, poll count, error status, clear-done marker, both logits, and all 32 counts with actual/expected values;
  - explicitly sends `CLEAR_DONE` after each case and retains the reset boundary between cases.
- `scripts/create_vitis_standalone_app.py`
  - uses Vitis 2025.1 `empty_application` and explicit `ps7_cortexa9_0` / `standalone_a9_0`;
  - does not pre-create the workspace directory, avoiding Vitis' “workspace version” error for an empty pre-created directory;
  - prints the XSA and ELF SHA-256 values;
  - validates the XSA/source file paths before invoking Vitis;
  - checks platform/application `.buildstatus` files and requires a real `.xpfm` and `.elf`, so Vitis process exit code cannot masquerade as an artifact.
- `scripts/export_golden_to_c.py`
  - retains the frozen golden JSON SHA-256 when generating the C header and manifest;
  - was lint-cleaned without changing the generated data contract.
- `include/snn_replay_regs.h` and `scripts/create_standalone_platform.tcl`
  - had UTF-8 BOM markers removed; their register/Tcl content is otherwise unchanged.
- `README.md`
  - now documents the HLS-6C input path, current blocked state, fresh-workspace rule, and evidence markers.

## 4. Vitis build attempts

### Attempt A — long workspace, first run

Workspace: `vivado/system/vitis_standalone_build_hls6c_20260728`  Platform: `snn_replay_platform_hls6c_20260728`  Application: `snn_replay_app_hls6c_20260728`

The Vitis invocation exceeded the 124-second shell limit while generating the platform. The retained status is:

```text
#Tue Jul 28 16:58:47 CST 2026
export=ERROR
```

No `.xpfm` or `.elf` exists in that workspace. The generated workspace is ignored by `snn_hybrid_eeg/.gitignore` and was retained as failure evidence.

### Attempt B — fresh workspace

Workspace: `vivado/system/vitis_standalone_build_hls6c_20260728_run2`  Platform: `snn_replay_platform_hls6c_run2_20260728`  Application: `snn_replay_app_hls6c_run2_20260728`

This run completed the Vitis command wrapper, but `platform.build()` returned `1`. The Vitis console reported platform creation and then failed while building the BSP:

```text
Platform creation finished successfully.
Platform Quick Build initiated.
[ERROR]: Command 'cmake --build . --parallel 22 --verbose' returned non-zero exit status 1.
[ERROR]: Failed to build the BSP
Error in generating platform.
```

The retained status is:

```text
#Tue Jul 28 17:06:06 CST 2026
export=ERROR
```

The workspace contains `CMakeError.log` compiler-identification dependency failures and Vitis emitted `CMAKE_OBJECT_PATH_MAX` warnings for generated paths close to the 250-character limit. These are recorded as contributing diagnostics, not as a proven single root cause because the leaf compiler diagnostic was not retained by Vitis. No `.xpfm` or `.elf` exists.

### Attempt C — short-path probe

Workspace: `D:\v6c_20260728`. The user interrupted this bounded retry before platform creation completed. Only Vitis metadata exists; there is no `.buildstatus`, `.xpfm`, or `.elf`. This run is not counted as validation.

The exact condensed evidence is retained in `vivado/system/reports/HLS6C_VITIS_PLATFORM_BUILD_EVIDENCE.txt`.

## 5. Board gate decision

Per the reviewed execution plan, the platform/domain/ELF stop gate applies. Therefore:

- HLS-6B bitstream was **not** downloaded by this HLS-6C execution;
- no UART1/COM capture was produced;
- no VERSION or first AXI-Lite transaction was observed on hardware;
- no checksum/status/logit/count comparison was made against the board;
- `board replay PASS` is **not** reported.

The next bounded action is to reproduce the platform BSP failure in a genuinely short workspace while capturing the leaf CMake/Ninja diagnostic, then rerun the same source/script. That action is outside this stopped execution because the user requested no further long-running Vitis process after the platform error.

## 6. Validation performed

- Golden JSON SHA-256 recomputed and matched `8f73683b4448f8315af76151e36dacff494197c0caf8bcf2e8ace01ad301604a`.
- XSA ZIP metadata inspected; target part and address segments were consistent with the HLS-6B contract.
- `python -m py_compile vivado/system/vitis/snn_replay_standalone/scripts/create_vitis_standalone_app.py` and `export_golden_to_c.py` passed.
- `python -m ruff check vivado/system/vitis/snn_replay_standalone/scripts` passed.
- Curated HLS-6C source, script, README, and report files were checked as UTF-8 without BOM and without trailing whitespace.
- `gcc -std=c11 -Wall -Wextra -Werror -fsyntax-only` passed for `src/main.c` with minimal Xilinx I/O stubs; this is a host syntax check, not an ARM/Vitis build.
- `git diff --check -- vivado/system/vitis/snn_replay_standalone` passed.
- No Vitis server/compiler helper processes from this execution remain. The pre-existing Vivado `hw_server` was left running.

## 7. Curated changed files

- `vivado/system/vitis/snn_replay_standalone/src/main.c`
- `vivado/system/vitis/snn_replay_standalone/scripts/create_vitis_standalone_app.py`
- `vivado/system/vitis/snn_replay_standalone/scripts/export_golden_to_c.py`
- `vivado/system/vitis/snn_replay_standalone/include/snn_replay_regs.h`
- `vivado/system/vitis/snn_replay_standalone/scripts/create_standalone_platform.tcl`
- `vivado/system/vitis/snn_replay_standalone/README.md`
- `vivado/system/reports/HLS6C_VITIS_PLATFORM_BUILD_EVIDENCE.txt`
- `vivado/system/reports/HLS6C_VITIS_BOARD_REPLAY.md`

No commit or push was performed.
