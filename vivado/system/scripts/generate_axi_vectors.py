#!/usr/bin/env python3
"""Generate AXI indexed-window memory images from the checked-in HLS golden JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def twos(value: int, bits: int) -> str:
    return f"{value & ((1 << bits) - 1):0{(bits + 3) // 4}X}"


def write_words(path: Path, values: list[int], bits: int) -> None:
    path.write_text("\n".join(twos(int(v), bits) for v in values) + "\n", encoding="utf-8", newline="\n")


def generate(golden: Path, out_dir: Path) -> None:
    data = json.loads(golden.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"schema_version": data["schema_version"], "cases": []}
    for case in data["cases"]:
        name = case["case_name"]
        features = [value for timestep in case["feature_current_q"] for value in timestep]
        weights = [value for row in case["weight_q"] for value in row]
        write_words(out_dir / f"{name}_feature.mem", features, 12)
        write_words(out_dir / f"{name}_weight.mem", weights, 12)
        write_words(out_dir / f"{name}_bias.mem", case["bias_q"], 12)
        write_words(out_dir / f"{name}_logits.mem", case["logits_q"], 18)
        write_words(out_dir / f"{name}_count.mem", case["spike_count"], 6)
        manifest["cases"].append({
            "case_name": name,
            "feature_words": len(features),
            "weight_words": len(weights),
            "bias_words": len(case["bias_q"]),
            "logit_words": len(case["logits_q"]),
            "count_words": len(case["spike_count"]),
            "source": str(golden.as_posix()),
        })
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", type=Path, default=Path("hls/hybrid_lif_head/golden/vectors_q12_6.json"))
    parser.add_argument("--out", type=Path, default=Path("vivado/system/vectors"))
    args = parser.parse_args()
    generate(args.golden, args.out)


if __name__ == "__main__":
    main()
