"""Run the staged SNN architecture ablation."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from dc_eeg.data import load_legacy_sadt_mat  # noqa: E402
from dc_eeg.experiment import resolve_device  # noqa: E402
from dc_eeg.snn_architecture import (  # noqa: E402
    aggregate_architecture_results,
    load_architecture_config,
    prepare_run,
    run_architecture_stage,
)
from dc_eeg.snn_pilot import load_config as load_pilot_config  # noqa: E402
from dc_eeg.snn_pilot import validate_pilot_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("experiments/channel8_snn_architecture/architecture.yaml"))
    parser.add_argument("--stage", choices=("smoke", "full"), required=True)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--run-id")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.config.expanduser()
    if not path.is_absolute():
        path = (REPOSITORY_ROOT / path).resolve()
    config = load_architecture_config(path, REPOSITORY_ROOT)
    pilot = load_pilot_config(config.base_config_path, REPOSITORY_ROOT)
    dataset = load_legacy_sadt_mat(pilot.dataset_path)
    validate_pilot_dataset(dataset, pilot)
    device = resolve_device(args.device)
    run_id = args.run_id or f"snn-architecture-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = config.results_root / run_id
    epochs = config.smoke_epochs if args.stage == "smoke" else config.full_epochs
    folds = [2] if args.stage == "smoke" else list(range(1, 12))
    print("[snn-architecture] run_id:", run_id)
    print("[snn-architecture] stage:", args.stage)
    print("[snn-architecture] architectures:", list(config.architectures))
    print("[snn-architecture] device:", device)
    print("[snn-architecture] jobs:", len(config.architectures) * len(folds))
    print("[snn-architecture] dataset_sha256:", dataset.metadata.sha256)
    if args.dry_run:
        return 0
    if not run_dir.exists():
        prepare_run(run_dir, config, dataset, run_id)
    result = run_architecture_stage(run_dir, list(config.architectures), folds, pilot, config, dataset, device, epochs, args.resume)
    print("[snn-architecture] stage summary:", result)
    if args.stage == "smoke":
        print("[snn-architecture] smoke complete; inspect metrics before launching full LOSO")
    else:
        print("[snn-architecture] aggregate:", aggregate_architecture_results(run_dir, list(config.architectures)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
