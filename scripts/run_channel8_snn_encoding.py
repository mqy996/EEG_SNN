"""Run the staged SNN input-encoding comparison."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from datetime import UTC, datetime

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from dc_eeg.experiment import resolve_device  # noqa: E402
from dc_eeg.snn_encoding import (  # noqa: E402
    ENCODERS,
    aggregate_encoding_results,
    load_encoding_config,
    prepare_run,
    run_encoding_stage,
)
from dc_eeg.snn_pilot import load_config as load_pilot_config  # noqa: E402
from dc_eeg.data import load_legacy_sadt_mat  # noqa: E402
from dc_eeg.snn_pilot import validate_pilot_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("experiments/channel8_snn_encoding/encoding.yaml"))
    parser.add_argument("--stage", choices=("smoke", "full"), required=True)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--run-id")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--encoding", choices=ENCODERS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.config.expanduser()
    if not path.is_absolute():
        path = (REPOSITORY_ROOT / path).resolve()
    config = load_encoding_config(path, REPOSITORY_ROOT)
    pilot = load_pilot_config(config.base_config_path, REPOSITORY_ROOT)
    dataset = load_legacy_sadt_mat(pilot.dataset_path)
    validate_pilot_dataset(dataset, pilot)
    device = resolve_device(args.device)
    encodings = [args.encoding] if args.encoding else list(config.encoders)
    if args.stage == "full" and tuple(encodings) != ENCODERS:
        raise ValueError("full encoding comparison must run exactly the configured three encoders")
    run_id = args.run_id or f"snn-encoding-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = config.results_root / run_id
    epochs = config.smoke_epochs if args.stage == "smoke" else config.full_epochs
    folds = [2] if args.stage == "smoke" else list(range(1, 12))
    jobs = len(encodings) * len(folds)
    print("[snn-encoding] run_id:", run_id)
    print("[snn-encoding] stage:", args.stage)
    print("[snn-encoding] encodings:", encodings)
    print("[snn-encoding] device:", device)
    print("[snn-encoding] jobs:", jobs)
    print("[snn-encoding] dataset_sha256:", dataset.metadata.sha256)
    if args.dry_run:
        return 0
    if not run_dir.exists():
        prepare_run(run_dir, config, pilot, dataset, run_id)
    result = run_encoding_stage(run_dir, encodings, folds, pilot, config, dataset, device, epochs, args.resume)
    print("[snn-encoding] stage summary:", result)
    if args.stage == "smoke":
        survivors = []
        import json
        for name in encodings:
            path = next((run_dir / "jobs").glob(f"{name}-seed{config.seed}-fold2/metrics.json"), None)
            if path is None:
                continue
            row = json.loads(path.read_text(encoding="utf-8"))
            if row.get("mean_spike_rate", 0) > 0.01 and row.get("mean_spike_rate", 1) < 0.50 and row.get("saturated_feature_ratio", 1) < 0.50:
                survivors.append(name)
        print("[snn-encoding] smoke survivors:", survivors)
    else:
        print("[snn-encoding] aggregate:", aggregate_encoding_results(run_dir, encodings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
