# E4 Vivado Resource, Timing, and Power Evidence

The authoritative E4 report is maintained in the Trellis task record:

`D:\eeg_fpga\.trellis\tasks\07-31-e4-vivado-resource-timing-power\E4_RESULTS.md`

This copy records the same evidence for the teacher-facing repository. The rebuilt system uses `xc7z020clg400-2`, `MT41J256M16 RE-125`, and a 50 MHz PL clock.

## Key results

- Full routed top: 8,902 LUT, 21,076 FF, 0 BRAM, 34 DSP.
- SNN AXI wrapper hierarchy: 8,416 LUT, 20,461 FF, 34 DSP.
- Integrated HLS instance: 7,725 LUT, 640 FF, 0 BRAM, 34 DSP.
- Post-implementation timing: WNS +4.776 ns, TNS 0, WHS +0.072 ns, THS 0 at 50 MHz.
- Routing: 26,818 fully routed nets, 0 routing errors.
- DRC: 0 errors.
- Full-system Vivado power estimate: 1.769 W (dynamic 1.626 W, static 0.143 W, medium confidence).
- HLS IP-only estimate: 0.129 W (dynamic 0.026 W, static 0.103 W, medium confidence).

Power values are Vivado estimates, not measured board power. The detailed report and SHA-256 manifest are in the Trellis task record and the `run_20260731_attempt1/artifacts` directory.
