"""Tests for the executable HLS-1 Q12.6 arithmetic contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dc_eeg.hls_contract import (
    BETA_Q,
    FEATURE_CHANNELS,
    MAX_Q,
    MIN_Q,
    NUM_CLASSES,
    THRESHOLD_Q,
    TIME_STEPS,
    channel_major_to_time_major,
    contract_worst_case_bounds,
    quantize_q12_6,
    round_half_even_div,
    run_q12_6_reference,
)


GOLDEN_PATH = Path(__file__).parents[1] / "hls/hybrid_lif_head/golden/vectors_q12_6.json"


def zero_currents() -> list[list[int]]:
    return [[0 for _ in range(FEATURE_CHANNELS)] for _ in range(TIME_STEPS)]


def simple_weights() -> list[list[int]]:
    return [[0 for _ in range(FEATURE_CHANNELS)] for _ in range(NUM_CLASSES)]


def test_round_half_even_div_is_symmetric_at_ties():
    assert round_half_even_div(1, 2) == 0
    assert round_half_even_div(3, 2) == 2
    assert round_half_even_div(5, 2) == 2
    assert round_half_even_div(-1, 2) == 0
    assert round_half_even_div(-3, 2) == -2
    assert round_half_even_div(-5, 2) == -2
    assert round_half_even_div(-7, 2) == -4


def test_round_half_even_div_rejects_non_positive_denominator():
    with pytest.raises(ValueError, match="positive"):
        round_half_even_div(1, 0)


def test_quantization_uses_q12_6_limits_and_ties_to_even():
    assert quantize_q12_6(0.5 / 64) == 0
    assert quantize_q12_6(1.5 / 64) == 2
    assert quantize_q12_6(-0.5 / 64) == 0
    assert quantize_q12_6(-1.5 / 64) == -2
    assert quantize_q12_6(MAX_Q / 64) == MAX_Q
    assert quantize_q12_6((MAX_Q + 1) / 64) == MAX_Q
    assert quantize_q12_6((MIN_Q - 1) / 64) == MIN_Q
    assert quantize_q12_6(10_000.0) == MAX_Q
    assert quantize_q12_6(-10_000.0) == MIN_Q


def test_threshold_equality_and_subtract_reset_are_explicit():
    currents = zero_currents()
    currents[0][0] = THRESHOLD_Q
    currents[1][0] = 1
    result = run_q12_6_reference(currents, simple_weights(), [0, 0])

    assert result["spikes"][0][0] == 1
    assert result["membrane_after_reset"][0][0] == 0
    assert result["membrane_after_reset"][1][0] == 1
    assert result["spike_count"][0] == 1


def test_signed_currents_do_not_create_negative_spikes():
    currents = zero_currents()
    currents[0][0] = MAX_Q
    currents[0][1] = MIN_Q
    currents[1][0] = -MAX_Q
    currents[1][1] = MAX_Q
    result = run_q12_6_reference(currents, simple_weights(), [0, 0])

    assert result["spikes"][0][0] == 1
    assert result["spikes"][0][1] == 0
    assert all(spike in (0, 1) for row in result["spikes"] for spike in row)
    assert result["membrane_after_reset"][0][1] == MIN_Q


def test_channel_major_to_time_major_maps_asymmetric_fixture():
    canonical = [[0 for _ in range(TIME_STEPS)] for _ in range(FEATURE_CHANNELS)]
    canonical[7][13] = THRESHOLD_Q + 1
    canonical[2][41] = THRESHOLD_Q

    time_major = channel_major_to_time_major(canonical)

    assert time_major[13][7] == THRESHOLD_Q + 1
    assert time_major[41][2] == THRESHOLD_Q
    assert time_major[7][13] == 0

    weights = simple_weights()
    weights[0][7] = 64
    result = run_q12_6_reference(time_major, weights, [0, 0])

    assert result["spikes"][13][7] == 1
    assert result["membrane_after_reset"][13][7] == 1
    assert result["logits_q"] == [1, 0]


def test_channel_major_to_time_major_validates_shape():
    with pytest.raises(ValueError, match="32 rows"):
        channel_major_to_time_major(zero_currents())


def test_contract_bounds_dominate_observed_case_ranges():
    bounds = contract_worst_case_bounds()
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    for case in payload["cases"]:
        assert case["range_report_scope"] == "case_observed_only"
        for name, observed in case["range_report"].items():
            assert name in bounds
            assert bounds[name]["min"] <= observed["min"]
            assert observed["max"] <= bounds[name]["max"]

    assert bounds["membrane_after_reset_q"] == {"min": -21856, "max": 21846}
    assert bounds["logits_q"] == {"min": -67584, "max": 67551}


def test_state_is_reset_between_calls():
    currents = zero_currents()
    currents[0][0] = THRESHOLD_Q
    first = run_q12_6_reference(currents, simple_weights(), [0, 0])
    second = run_q12_6_reference(zero_currents(), simple_weights(), [0, 0])

    assert first["spike_count"][0] == 1
    assert second["spike_count"] == [0] * FEATURE_CHANNELS
    assert second["membrane_after_reset"] == zero_currents()


def test_shape_and_external_range_validation():
    with pytest.raises(ValueError, match="48 rows"):
        run_q12_6_reference([], simple_weights(), [0, 0])
    currents = zero_currents()
    currents[0][0] = MAX_Q + 1
    with pytest.raises(ValueError, match="Q12.6 range"):
        run_q12_6_reference(currents, simple_weights(), [0, 0])
    with pytest.raises(ValueError, match="beta_q"):
        run_q12_6_reference(zero_currents(), simple_weights(), [0, 0], beta_q=BETA_Q - 1)


def test_golden_vectors_recompute_from_saved_inputs():
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert payload["contract_metadata"]["scale"] == 64
    assert payload["contract_metadata"]["input_layout"] == "time_major_[48][32]"
    assert payload["contract_metadata"]["range_report_scope"] == "case_observed_only"
    assert payload["contract_metadata"]["contract_domain_bounds_scope"] == (
        "mathematically_justified_safe_bound"
    )
    assert [case["case_name"] for case in payload["cases"]] == [
        "threshold_edge",
        "signed_currents",
        "rounding_and_reset",
    ]
    for case in payload["cases"]:
        recomputed = run_q12_6_reference(
            case["feature_current_q"], case["weight_q"], case["bias_q"]
        )
        for key in (
            "spikes",
            "membrane_after_reset",
            "spike_count",
            "rate_q",
            "logits_q",
            "range_report",
        ):
            assert case[key] == recomputed[key], key
        assert len(case["spikes"]) == TIME_STEPS
        assert len(case["spikes"][0]) == FEATURE_CHANNELS


