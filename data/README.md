# Dataset boundary

The official balanced SADT MAT file is intentionally not stored in this repository.

Place it at:

```text
data/dataset.mat
```

Expected SHA-256:

```text
53cc4ef14b1343f7f3fb5322dd2b541c031c6c2297bddf1817aed04dc687a6a4
```

Expected metadata:

```text
samples: 2022
channels: 30
timepoints: 384
subjects: 11
order_kind: class_blocked_compatibility
```

The data order is not a chronological replay manifest. Do not reorder or modify the official data
when reproducing the compatibility experiments.
