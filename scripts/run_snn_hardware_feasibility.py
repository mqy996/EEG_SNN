"""Run the software-only fixed-point feasibility probe."""

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
from dc_eeg.snn_hardware import load_hardware_config, run_feasibility_probe, write_probe_result  # noqa: E402
from dc_eeg.snn_pilot import load_config as load_pilot_config  # noqa: E402
from dc_eeg.snn_pilot import validate_pilot_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("experiments/channel8_snn_hardware/hardware.yaml"))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--run-id")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.config.expanduser()
    if not path.is_absolute():
        path = (REPOSITORY_ROOT / path).resolve()
    config = load_hardware_config(path, REPOSITORY_ROOT)
    pilot = load_pilot_config(config.base_config_path, REPOSITORY_ROOT)
    dataset = load_legacy_sadt_mat(pilot.dataset_path)
    validate_pilot_dataset(dataset, pilot)
    device = resolve_device(args.device)
    run_id = args.run_id or f"snn-hardware-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    output = config.results_root / run_id / "feasibility.json"
    print("[snn-hardware] run_id:", run_id)
    print("[snn-hardware] target:", config.target_part, "@", config.clock_mhz, "MHz")
    print("[snn-hardware] input_format:", config.input_format)
    print("[snn-hardware] fixed_points:", [(item.total_bits, item.frac_bits) for item in config.fixed_points])
    print("[snn-hardware] device:", device)
    print("[snn-hardware] dataset_sha256:", dataset.metadata.sha256)
    if args.dry_run:
        return 0
    result = run_feasibility_probe(dataset, pilot, config, device)
    result["run_id"] = run_id
    result["dataset_sha256"] = dataset.metadata.sha256
    write_probe_result(output, result)
    print("[snn-hardware] output:", output)
    print("[snn-hardware] decision:", result["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
