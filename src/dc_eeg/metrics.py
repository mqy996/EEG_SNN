"""Small dependency-free binary classification metrics for subject-level evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class BinaryMetrics:
    accuracy: float
    macro_f1: float
    balanced_accuracy: float
    sensitivity: float
    specificity: float
    samples: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def binary_metrics(labels: np.ndarray, predictions: np.ndarray) -> BinaryMetrics:
    y_true = np.asarray(labels).reshape(-1).astype(np.int64, copy=False)
    y_pred = np.asarray(predictions).reshape(-1).astype(np.int64, copy=False)
    if y_true.shape != y_pred.shape or not y_true.size:
        raise ValueError("labels and predictions must be non-empty arrays with equal shape")
    if not np.isin(y_true, (0, 1)).all() or not np.isin(y_pred, (0, 1)).all():
        raise ValueError("binary metrics require labels and predictions encoded as 0/1")

    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    sensitivity = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1_scores = []
    for label in (0, 1):
        true_positive = int(np.sum((y_true == label) & (y_pred == label)))
        false_positive = int(np.sum((y_true != label) & (y_pred == label)))
        false_negative = int(np.sum((y_true == label) & (y_pred != label)))
        denom = 2 * true_positive + false_positive + false_negative
        f1_scores.append((2 * true_positive / denom) if denom else 0.0)
    return BinaryMetrics(
        accuracy=float(np.mean(y_true == y_pred)),
        macro_f1=float(np.mean(f1_scores)),
        balanced_accuracy=(sensitivity + specificity) / 2.0,
        sensitivity=sensitivity,
        specificity=specificity,
        samples=int(y_true.size),
    )


def aggregate_subject_metrics(metrics: list[BinaryMetrics]) -> dict[str, dict[str, float]]:
    if not metrics:
        raise ValueError("at least one subject metric is required")
    keys = ("accuracy", "macro_f1", "balanced_accuracy", "sensitivity", "specificity")
    return {
        "subject_mean": {key: float(np.mean([getattr(item, key) for item in metrics])) for key in keys},
        "subject_std": {key: float(np.std([getattr(item, key) for item in metrics])) for key in keys},
    }
