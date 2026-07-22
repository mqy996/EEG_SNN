# SNN-4 Fixed-Point / FPGA Feasibility

Status: **software feasibility gate passed; HLS is the next gated step**.

The selected contract is Channel8 + GroupNorm, direct-current encoding and Hybrid LIF head on
`xc7z020clg400-1` at an assumed 100 MHz. Q12.6 is the first HLS candidate: it reached 99.24%
prediction agreement with 0.03 percentage-point spike-rate drift in the fold-2 probe. Q8.4
fell below the 99% agreement target; Q16.8 is retained as a high-fidelity reference.

This remains a head-level software probe. No board, HLS csim, Vivado resource, timing or power
claim is made. See `RESULTS.md` and the ignored run artifact for details.
