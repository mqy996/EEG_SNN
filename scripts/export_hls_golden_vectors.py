"""Export and validate deterministic HLS-1 Q12.6 golden vectors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from dc_eeg.hls_contract import (  # noqa: E402
    FEATURE_CHANNELS,
    MAX_Q,
    MIN_Q,
    SCHEMA_VERSION,
    THRESHOLD_Q,
    TIME_STEPS,
    contract_metadata,
    run_q12_6_reference,
)

DEFAULT_OUTPUT = REPOSITORY_ROOT / "hls/hybrid_lif_head/golden/vectors_q12_6.json"


def _matrix(fill: int = 0) -> list[list[int]]:
    return [[fill for _ in range(FEATURE_CHANNELS)] for _ in range(TIME_STEPS)]


def _weights(case_index: int) -> list[list[int]]:
    return [
        [((channel + 1) * (case_index + 2) * 8) - 128 for channel in range(FEATURE_CHANNELS)],
        [128 - ((channel + 1) * (case_index + 3) * 6) for channel in range(FEATURE_CHANNELS)],
    ]


def _threshold_edge_case() -> list[list[int]]:
    currents = _matrix()
    # Channel 0 reaches threshold exactly once; channel 1 demonstrates a
    # continuous threshold current and therefore emits on every time step.
    currents[0][0] = THRESHOLD_Q
    for time_index in range(TIME_STEPS):
        currents[time_index][1] = THRESHOLD_Q
    currents[0][2] = THRESHOLD_Q + 1
    currents[1][2] = -1
    currents[2][3] = THRESHOLD_Q * 2 + 3
    currents[3][3] = -THRESHOLD_Q
    return currents


def _signed_currents_case() -> list[list[int]]:
    currents = [
        [((time_index * 17 - channel * 23) % 129) - 64 for channel in range(FEATURE_CHANNELS)]
        for time_index in range(TIME_STEPS)
    ]
    currents[0][0] = MAX_Q
    currents[0][1] = MIN_Q
    currents[0][2] = 0
    currents[1][0] = THRESHOLD_Q
    currents[1][1] = -THRESHOLD_Q
    return currents


def _rounding_and_reset_case() -> list[list[int]]:
    currents = _matrix()
    # At t=1, beta_q * (+/-16) / 64 is +/-14.5.  This exercises both
    # signs of the exact midpoint rule before later threshold activity.
    currents[0][0] = 16
    currents[0][1] = -16
    currents[2][0] = THRESHOLD_Q
    currents[2][1] = -THRESHOLD_Q
    currents[4][2] = 31
    currents[5][2] = 1
    currents[6][3] = 63
    currents[7][3] = -31
    return currents


def build_golden_payload() -> dict[str, Any]:
    """Build all fixed synthetic cases without reading data or checkpoints."""

    cases = []
    case_inputs = (
        ("threshold_edge", _threshold_edge_case()),
        ("signed_currents", _signed_currents_case()),
        ("rounding_and_reset", _rounding_and_reset_case()),
    )
    for case_index, (case_name, currents) in enumerate(case_inputs):
        result = run_q12_6_reference(
            currents,
            _weights(case_index),
            [case_index * 7 - 16, 24 - case_index * 5],
        )
        result["case_name"] = case_name
        cases.append(result)

    return {
        "schema_version": SCHEMA_VERSION,
        "contract_metadata": contract_metadata(),
        "generation": {
            "source": "fixed synthetic Q12.6 vectors",
            "contains_raw_eeg": False,
            "contains_checkpoints": False,
            "case_count": len(cases),
        },
        "cases": cases,
    }


def canonical_json(payload: dict[str, Any]) -> str:
    """Serialize with stable ordering and a final newline."""

    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="check the existing file against freshly generated vectors without writing",
    )
    return parser.parse_args()


def resolve_output(path: Path) -> Path:
    return path.expanduser().resolve() if path.is_absolute() else (REPOSITORY_ROOT / path).resolve()


def main() -> int:
    args = parse_args()
    output = resolve_output(args.output)
    expected = canonical_json(build_golden_payload())
    if args.check:
        if not output.exists():
            print(f"golden file is missing: {output}", file=sys.stderr)
            return 1
        actual = output.read_text(encoding="utf-8")
        if actual != expected:
            print(f"golden file differs from deterministic export: {output}", file=sys.stderr)
            return 1
        print(f"golden check passed: {output}")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(expected, encoding="utf-8", newline="\n")
    print(f"golden vectors written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

