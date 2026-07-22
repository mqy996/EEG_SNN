"""Deterministic subject-independent leave-one-subject-out splits."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LosoSplit:
    held_out_subject: int
    train_indices: np.ndarray
    test_indices: np.ndarray


def iter_loso_splits(subject_ids: np.ndarray, fold: int | None = None) -> list[LosoSplit]:
    """Build subject-disjoint LOSO splits, optionally for one held-out subject."""

    ids = np.asarray(subject_ids).reshape(-1).astype(np.int64, copy=False)
    subjects = [int(value) for value in np.unique(ids)]
    if len(subjects) < 2:
        raise ValueError("LOSO requires at least two distinct subjects")
    if fold is not None and fold not in subjects:
        raise ValueError(f"requested fold {fold} is not present; available={subjects}")

    selected = [fold] if fold is not None else subjects
    splits: list[LosoSplit] = []
    for held_out in selected:
        test_indices = np.flatnonzero(ids == held_out)
        train_indices = np.flatnonzero(ids != held_out)
        if not test_indices.size or not train_indices.size:
            raise ValueError(f"invalid LOSO split for subject {held_out}")
        if np.intersect1d(train_indices, test_indices).size:
            raise AssertionError("LOSO train/test indices overlap")
        splits.append(LosoSplit(held_out, train_indices, test_indices))
    return splits


def split_manifest(splits: list[LosoSplit], subject_ids: np.ndarray) -> dict[str, object]:
    """Return a compact, serializable split description without raw EEG data."""

    ids = np.asarray(subject_ids).reshape(-1)
    return {
        "protocol": "leave_one_subject_out",
        "folds": [
            {
                "held_out_subject": split.held_out_subject,
                "train_samples": int(split.train_indices.size),
                "test_samples": int(split.test_indices.size),
                "train_subjects": [
                    int(value) for value in np.unique(ids[split.train_indices])
                ],
                "test_subjects": [
                    int(value) for value in np.unique(ids[split.test_indices])
                ],
            }
            for split in splits
        ],
    }
