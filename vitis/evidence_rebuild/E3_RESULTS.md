# E3 board latency/throughput task status

- Date: 2026-07-31
- Task: `07-31-e3-board-latency-throughput`
- Status: `STOPPED_AFTER_TWO_ATTEMPTS`
- Device contract: `xc7z020clg400-2`, DDR `MT41J256M16 RE-125`, FCLK0 `50 MHz`.

## Work completed

- Created timing application source:
  - `snn_hybrid_eeg/vitis/evidence_rebuild/latency_source/main.c`
  - `snn_hybrid_eeg/vitis/evidence_rebuild/latency_source/snn_multisample_vectors.h`
- Created Vitis application component:
  - `snn_hybrid_eeg/vitis/e1/snn_latency_replay`
- The source measures three explicitly separated scopes:
  - AXI-Lite input loading
  - `START` write to `DONE` status
  - full replay from reset/input load to `DONE`
- The source also retains checksum/logit/count verification and reports replay accuracy and throughput.

## Attempt log

### Attempt 1 — source compilation failure

The Vitis 2025.1 application was created successfully, but compilation stopped because the standalone BSP did not expose `xtime_l.h` through the generated application include path:

`fatal error: xtime_l.h: No such file or directory`

Bounded fix applied: copied the BSP's exact `xtime_l.h` into the application `src/` directory. The header is only a declaration/interface header; the timer implementation remains supplied by the generated BSP library.

### Attempt 2 — workspace lock

A second build attempt was issued, but Vitis could not open the existing workspace:

`Cannot set workspace ... The workspace 'D:\eeg_fpga\snn_hybrid_eeg\vitis\e1' is already in use.`

Per the project rule, no third attempt was made. The task is therefore stopped and requires user confirmation/lock cleanup before continuing.

## Not yet available

- `snn_latency_replay.elf` was not generated.
- No XSDB board run was attempted.
- No measured board latency/throughput result is claimed.

## Recovery action to authorize later

After confirming that no Vitis process is using the workspace, clear only the stale workspace lock using the Vitis Unified workflow's lock-cleanup procedure, then rerun the application build once. Do not change the FPGA part, DDR contract, clock, PS7 configuration, or AXI topology.

## Follow-up build log supplied by user (2026-07-31 15:45:37)

The user supplied a later Vitis build log for `snn_latency_replay`. This confirms that the workspace was opened and compilation progressed further, but the second bounded build attempt failed on a BSP timer macro mismatch:

```text
XPAR_CPU_CORTEXA9_0_CPU_CLK_FREQ_HZ undeclared
suggested: XPAR_CPU_CORTEXA9_CORE_CLOCK_FREQ_HZ
```

Interpretation: this is a software-header compatibility issue caused by copying the BSP's `xtime_l.h` into the application. It is not evidence of a wrong FPGA part, DDR setting, PS7 configuration, SmartConnect topology, or HLS IP failure. The generated Vitis 2025.1 `xparameters.h` uses `XPAR_CPU_CORTEXA9_CORE_CLOCK_FREQ_HZ`, while that copied header expects the older/alternate macro name.

The task remains stopped under the two-attempt rule. No third build or workaround was attempted. A future bounded fix should use the generated timer interface (`xiltimer.h`) or a source-local compatibility alias, then rebuild once.

## Bounded repair round — timer header compatibility (2026-07-31)

- Authorized scope: source-only timer compatibility repair; no FPGA/XSA/XPFM/AXI changes.
- Source change: `snn_hybrid_eeg/vitis/e1/snn_latency_replay/src/main.c`
  - Replaced the copied `xtime_l.h` include with the generated BSP's `xiltimer.h`.
  - This uses the Vitis 2025.1 BSP timer interface, including `XTime`, `XTime_GetTime`, and `COUNTS_PER_SECOND`, without the legacy CPU-clock macro dependency.
- `src/xtime_l.h` was not modified.

### Build verification

The Vitis Python API invocation could not open the workspace because the Vitis Unified IDE already held the workspace lock. The one actual generated Vitis application build was then run directly with the Vitis 2025.1 application build utility:

```powershell
& 'D:\vitis\2025.1\Vivado\bin\empyro.bat' build_app `
  -s 'D:\eeg_fpga\snn_hybrid_eeg\vitis\e1\snn_latency_replay\src' `
  -b 'D:\eeg_fpga\snn_hybrid_eeg\vitis\e1\snn_latency_replay\build'
```

Result:

- `main.c` compiled successfully after the timer-header change.
- Link failed because the generated hello-world template source still defines a second `main`:
  - `src/helloworld.c:26: multiple definition of 'main'`
  - `src/main.c:183: first defined here`
- `snn_latency_replay.elf` was not generated.
- No further repair or build attempt was made, per the bounded-failure instruction.

Status: `STOP_AND_REPORT_AFTER_TIMER_FIX_LINK_ERROR`

## Board latency run analysis supplied by user

The `snn_latency_replay` board run completed functional replay successfully:

- Device contract printed: `xc7z020clg400-2`, `MT41J256M16 RE-125`, FCLK0 50 MHz.
- 314/314 cases passed checksum/output verification.
- Classification result: `277/314`, 88.2166% (the printed integer percentage is 88.21%).
- Mean polling count: 93; this is an ARM polling observation, not an FPGA cycle count.

The measured time fields are invalid and must not be reported:

```text
axil_us=0
compute_us=0
total_us=0
sum_us=0
mean_samples_per_s_x100=4294967295
```

Root cause identified from the Vitis 2025.1 BSP implementation: `XTime_GetTime()` reads the Zynq global timer, but the timer is only started by the default timer implementation when its sleep interval function is first invoked. The application reads timestamps before any timer-starting sleep call, so the counter remains at zero. The throughput value is an unsigned underflow artifact from division by zero.

The valid result is therefore hardware replay correctness and accuracy only. A future measurement fix must start the BSP timer once before the first timestamp (for example through the generated `usleep`/xiltimer path), then rerun the board test. No latency/throughput claim is made from this run.

## Valid board timing result (user run, 2026-07-31)

The timer self-check passed and the full 314-sample board replay produced non-zero timing values.

| Metric | Result |
|---|---:|
| Replay consistency | 314/314 PASS |
| Classification | 277/314 = 88.2166% |
| AXI-Lite input load | 317 us/sample |
| START-to-DONE PS-observed compute scope | 8 us/sample |
| Full reset + load + START-to-DONE | 326 us/sample |
| Full-replay throughput | 3067.48 samples/s |
| Mean ARM polling count | 93 |

The throughput field is printed as `mean_samples_per_s_x100=306748`; divide by 100 before reporting it. The measured scopes are PS-observed software-to-AXI transaction scopes, not HLS RTL cycle counts. The prior HLS standalone report recorded 1687 cycles (~33.74 us at 50 MHz), so that figure must remain separate until the scope/design-version discrepancy is reconciled. Do not claim that the 8 us PS-observed value is the HLS kernel latency without further analysis.
