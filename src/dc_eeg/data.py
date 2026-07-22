"""Validated data access for the legacy CompactCNN compatibility artifact.

The currently supported MAT source is intentionally marked as compatibility-only:
its array order must not be used as chronological replay. Task B will add a
separate manifest-backed chronological loader.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import numpy as np
from scipy.io import loadmat


ALL_30_CHANNELS: tuple[str, ...] = (
    "Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "FT7", "FC3", "FCZ",
    "FC4", "FT8", "T3", "C3", "Cz", "C4", "T4", "TP7", "CP3", "CPz",
    "CP4", "TP8", "T5", "P3", "PZ", "P4", "T6", "O1", "Oz", "O2",
)
CHANNEL8_NAMES: tuple[str, ...] = ("C3", "Cz", "C4", "CP3", "CPz", "CP4", "Oz", "O2")
CHANNEL8_INDICES: tuple[int, ...] = tuple(ALL_30_CHANNELS.index(name) for name in CHANNEL8_NAMES)


class DataContractError(ValueError):
    """Raised when a local EEG artifact does not satisfy the runner contract."""


@dataclass(frozen=True)
class EEGDatasetMetadata:
    source_path: str
    sha256: str
    samples: int
    channels: int
    timepoints: int
    labels: dict[str, int]
    subjects: tuple[int, ...]
    order_kind: str


@dataclass(frozen=True)
class EEGDataset:
    samples: np.ndarray  # [N, C, T], float64/float32
    labels: np.ndarray  # [N], int64
    subject_ids: np.ndarray  # [N], int64
    metadata: EEGDatasetMetadata


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalise_samples(raw: np.ndarray, n_samples: int) -> np.ndarray:
    if raw.ndim != 3:
        raise DataContractError(f"EEGsample must be 3-D, got shape {raw.shape}")
    if raw.shape[0] == n_samples:
        samples = raw
    elif raw.shape[-1] == n_samples:
        samples = np.transpose(raw, (2, 0, 1))
    elif raw.shape[1] == n_samples:
        samples = np.transpose(raw, (1, 0, 2))
    else:
        raise DataContractError(
            "cannot infer sample axis: no EEGsample dimension matches label count "
            f"{n_samples}; shape={raw.shape}"
        )
    if samples.shape[1] <= 0 or samples.shape[2] <= 0:
        raise DataContractError(f"invalid channel/time dimensions after normalization: {samples.shape}")
    return np.ascontiguousarray(samples)


def _detect_order_kind(labels: np.ndarray, subject_ids: np.ndarray) -> str:
    """Classify the known legacy order without claiming real chronology."""

    transitions = []
    for subject in np.unique(subject_ids):
        subject_labels = labels[subject_ids == subject]
        transitions.append(int(np.count_nonzero(subject_labels[1:] != subject_labels[:-1])))
    if transitions and max(transitions) <= 1:
        return "class_blocked_compatibility"
    return "legacy_order_not_verified_chronological"


def load_legacy_sadt_mat(path: str | Path) -> EEGDataset:
    """Load the historical MAT artifact as a non-chronological compatibility dataset."""

    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"EEG MAT file not found: {source}")
    try:
        mat = loadmat(source)
    except NotImplementedError as exc:
        raise DataContractError(
            "MAT v7.3/HDF5 is not supported by this compatibility loader; "
            "use the future chronological manifest loader"
        ) from exc

    required = ("EEGsample", "substate", "subindex")
    missing = [key for key in required if key not in mat]
    if missing:
        raise DataContractError(f"MAT file is missing required keys: {missing}")

    labels = np.asarray(mat["substate"]).reshape(-1).astype(np.int64, copy=False)
    subject_ids = np.asarray(mat["subindex"]).reshape(-1).astype(np.int64, copy=False)
    if labels.size == 0:
        raise DataContractError("MAT file contains no labels")
    if labels.shape != subject_ids.shape:
        raise DataContractError("label and subject arrays must have the same shape")
    if not np.isin(labels, (0, 1)).all():
        raise DataContractError("compatibility runner requires binary labels encoded as 0/1")
    if (subject_ids <= 0).any():
        raise DataContractError("subject IDs must be positive integers")

    samples = _normalise_samples(np.asarray(mat["EEGsample"]), labels.size)
    if samples.shape[0] != labels.size:
        raise DataContractError("sample count differs from label count after layout normalization")

    unique_labels, label_counts = np.unique(labels, return_counts=True)
    subjects = tuple(int(value) for value in np.unique(subject_ids))
    metadata = EEGDatasetMetadata(
        source_path=str(source),
        sha256=sha256_file(source),
        samples=int(samples.shape[0]),
        channels=int(samples.shape[1]),
        timepoints=int(samples.shape[2]),
        labels={str(int(label)): int(count) for label, count in zip(unique_labels, label_counts)},
        subjects=subjects,
        order_kind=_detect_order_kind(labels, subject_ids),
    )
    return EEGDataset(samples=samples, labels=labels, subject_ids=subject_ids, metadata=metadata)


def select_channels(samples: np.ndarray, channel_indices: tuple[int, ...] = CHANNEL8_INDICES) -> np.ndarray:
    """Select an explicit channel subset from `[N, C, T]` samples."""

    if samples.ndim != 3:
        raise DataContractError(f"expected [N, C, T] samples, got {samples.shape}")
    if not channel_indices:
        raise DataContractError("at least one channel index is required")
    if min(channel_indices) < 0 or max(channel_indices) >= samples.shape[1]:
        raise DataContractError(
            f"channel indices {channel_indices} are invalid for {samples.shape[1]} channels"
        )
    return np.ascontiguousarray(samples[:, channel_indices, :])
