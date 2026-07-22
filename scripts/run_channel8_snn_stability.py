"""Run the staged, resumable SNN beta/threshold stability sweep."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from dc_eeg.snn_stability import (  # noqa: E402
    STAGES,
    build_jobs,
    execute_stage,
    load_dataset_and_pilot,
    load_stability_config,
    make_run_id,
    prepare_run,
    rank_screen_configs,
    resolve_device_for_cli,
    resolve_run_directory,
    smoke_survivors,
    stability_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("experiments/channel8_snn_stability/sweep.yaml"),
    )
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--run-id", help="existing run ID for resume or explicit new ID")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config-id", choices=("S1", "S2", "S3", "S4"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.expanduser()
    if not config_path.is_absolute():
        config_path = (REPOSITORY_ROOT / config_path).resolve()
    stability = load_stability_config(config_path, REPOSITORY_ROOT)
    pilot, dataset = load_dataset_and_pilot(stability, REPOSITORY_ROOT)
    device = resolve_device_for_cli(args.device)

    run_id = args.run_id or make_run_id()
    run_dir = resolve_run_directory(stability, run_id)
    if args.stage == "smoke":
        ids = [args.config_id] if args.config_id else list(stability.configs)
    elif args.stage == "screen-loso":
        if not run_dir.is_dir():
            raise FileNotFoundError("screen-loso requires an existing smoke run; pass --run-id")
        ids = smoke_survivors(run_dir, stability)
        if args.config_id:
            ids = [args.config_id] if args.config_id in ids else []
    else:
        ids = None

    if args.stage == "stability" and not run_dir.is_dir():
        raise FileNotFoundError("stability requires an existing run with selection.json")

    jobs = build_jobs(args.stage, stability, run_dir, ids) if run_dir.is_dir() else []
    if args.dry_run:
        print("[snn-stability] run_id:", run_id)
        print("[snn-stability] stage:", args.stage)
        print("[snn-stability] device:", device)
        print("[snn-stability] dataset_sha256:", dataset.metadata.sha256)
        print("[snn-stability] config_ids:", ids if ids is not None else "selection.json")
        if jobs:
            print("[snn-stability] planned_jobs:", len(jobs))
        elif args.stage == "smoke":
            print("[snn-stability] planned_jobs:", len(ids or []))
        else:
            print("[snn-stability] planned_jobs: unavailable until prior stage artifacts exist")
        return 0

    if not run_dir.is_dir():
        prepare_run(run_dir, stability, pilot, dataset, device, run_id)
    if args.stage == "screen-loso" and not ids:
        selection = {"survivors": [], "ranked": [], "selected": [], "selection_gate_passed": False}
        from dc_eeg.artifacts import write_json

        write_json(run_dir / "selection.json", selection)
        print("[snn-stability] no smoke survivors; SNN-1 no-go")
        return 0

    summary = execute_stage(
        run_dir,
        stability,
        pilot,
        dataset,
        device,
        args.stage,
        ids,
        args.resume,
    )
    print("[snn-stability] stage summary:", summary)
    if args.stage == "smoke":
        survivors = smoke_survivors(run_dir, stability)
        print("[snn-stability] smoke survivors:", survivors)
    elif args.stage == "screen-loso":
        selection = rank_screen_configs(run_dir, stability, ids or [])
        print("[snn-stability] selected:", selection["selected"])
    else:
        result = stability_summary(run_dir, stability)
        print("[snn-stability] SNN-1 gate passed:", result["snn1_gate_passed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
