"""Run the matched Channel8 ANN versus Hybrid-SNN compatibility pilot."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from dc_eeg.data import load_legacy_sadt_mat  # noqa: E402
from dc_eeg.experiment import resolve_device  # noqa: E402
from dc_eeg.snn_pilot import (  # noqa: E402
    load_config,
    make_run_id,
    mark_pilot_failed,
    prepare_pilot_run,
    train_and_evaluate_pilot_fold,
    validate_pilot_dataset,
    write_pilot_artifacts,
)
from dc_eeg.splits import iter_loso_splits  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("experiments/channel8_hybrid_snn_pilot/pilot.yaml"),
    )
    parser.add_argument("--fold", type=int, help="run one held-out subject")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--dry-run", action="store_true", help="validate only; write no results")
    parser.add_argument("--smoke", action="store_true", help="use the short smoke epoch count")
    parser.add_argument("--run-id", help="optional explicit ignored result directory name")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.expanduser()
    if not config_path.is_absolute():
        config_path = (REPOSITORY_ROOT / config_path).resolve()
    config = load_config(config_path, REPOSITORY_ROOT)
    dataset = load_legacy_sadt_mat(config.dataset_path)
    validate_pilot_dataset(dataset, config)
    device = resolve_device(args.device)
    splits = iter_loso_splits(dataset.subject_ids, args.fold)
    epochs = config.smoke_epochs if args.smoke else config.epochs

    print("[snn-pilot] dataset:", dataset.metadata.source_path)
    print("[snn-pilot] sha256:", dataset.metadata.sha256)
    print("[snn-pilot] order_kind:", dataset.metadata.order_kind)
    print("[snn-pilot] device:", device)
    print("[snn-pilot] epochs:", epochs)
    print("[snn-pilot] folds:", ", ".join(str(item.held_out_subject) for item in splits))
    print("[snn-pilot] models: matched ann_groupnorm, hybrid_snn_groupnorm")
    print("[snn-pilot] claim: compatibility pilot only; not chronological or energy evidence")
    if args.dry_run:
        print("[snn-pilot] dry_run: validation complete; no result directory created")
        return 0

    run_id = args.run_id or make_run_id(config.seed, args.smoke)
    run_dir = config.results_root / run_id
    prepare_pilot_run(run_dir, config, dataset, splits, device, epochs, args.smoke)
    results = []
    try:
        for split in splits:
            for model_kind in ("ann", "snn"):
                print(
                    f"[snn-pilot] fold={split.held_out_subject} model={model_kind} "
                    f"train={len(split.train_indices)} test={len(split.test_indices)}"
                )
                result = train_and_evaluate_pilot_fold(
                    dataset,
                    split,
                    config,
                    device,
                    model_kind,
                    epochs,
                )
                results.append(result)
                spike_text = (
                    "n/a"
                    if result.mean_spike_rate is None
                    else f"{result.mean_spike_rate:.4f}"
                )
                print(
                    f"[snn-pilot] fold={split.held_out_subject} model={model_kind} "
                    f"accuracy={result.metrics.accuracy:.4f} "
                    f"macro_f1={result.metrics.macro_f1:.4f} spike_rate={spike_text}"
                )
        evidence = write_pilot_artifacts(
            run_dir,
            config,
            dataset,
            splits,
            device,
            results,
            epochs,
            args.smoke,
        )
    except BaseException as error:
        mark_pilot_failed(run_dir, error)
        raise
    print("[snn-pilot] results:", run_dir)
    print("[snn-pilot] completion:", evidence["completion"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
