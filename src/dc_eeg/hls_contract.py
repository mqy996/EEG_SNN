"""Executable Q12.6 integer contract for the HLS-1 Hybrid LIF head.

This module is deliberately independent from :mod:`dc_eeg.snn_hardware`.
The latter contains the historical software feasibility reference and must not
be changed to adopt this contract retroactively.
"""

from __future__ import annotations

from collections.abc import Sequence
import math
from numbers import Integral
from typing import Any, TypeAlias

SCALE = 64
MIN_Q = -2048
MAX_Q = 2047
TIME_STEPS = 48
FEATURE_CHANNELS = 32
NUM_CLASSES = 2
BETA_Q = 58
THRESHOLD_Q = 32
SCHEMA_VERSION = "hls-q12.6-golden-v1"

IntMatrix: TypeAlias = list[list[int]]
IntVector: TypeAlias = list[int]

_INT64_MIN = -(1 << 63)
_INT64_MAX = (1 << 63) - 1

# Safe invariant for the post-reset membrane over every accepted current
# sequence.  For any integer n, round_half_even_div(n, SCALE) is within one
# integer of n / SCALE.  Therefore the recurrence is bounded by
#   m_next >= (58 / 64) * m - 2049
#   m_next <= (58 / 64) * m + 2048
# (subtract-reset can only reduce the upper side and never lowers a value below
# zero).  The fixed-point enclosure [-21856, 21846] is consequently an
# invariant from the zero initial state.  HLS-2 width planning must use the
# returned contract-domain bounds, not the observed ranges of synthetic cases.
_MEMBRANE_MIN_Q = -21856
_MEMBRANE_MAX_Q = 21846
RANGE_REPORT_SCOPE = "case_observed_only"


def round_half_even_div(numerator: int, denominator: int) -> int:
    """Divide by a positive integer using symmetric round-half-to-even.

    Python's ``//`` rounds negative values toward negative infinity, while C/C++
    signed division rounds toward zero.  The HLS contract therefore defines the
    operation from absolute values so that positive and negative ties behave in
    exactly the same way.
    """

    if not isinstance(numerator, Integral) or isinstance(numerator, bool):
        raise TypeError("numerator must be an integer")
    if not isinstance(denominator, Integral) or isinstance(denominator, bool):
        raise TypeError("denominator must be an integer")
    denominator = int(denominator)
    if denominator <= 0:
        raise ValueError("denominator must be positive")

    numerator = int(numerator)
    sign = -1 if numerator < 0 else 1
    quotient, remainder = divmod(abs(numerator), denominator)
    twice_remainder = 2 * remainder
    if twice_remainder > denominator or (
        twice_remainder == denominator and quotient % 2 == 1
    ):
        quotient += 1
    return sign * quotient


def quantize_q12_6(value: float | int) -> int:
    """Quantize one real value to saturated signed Q12.6."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be a real scalar")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    rounded = int(round(value * SCALE))
    return max(MIN_Q, min(MAX_Q, rounded))


# A short alias is useful at call sites that already use the Q12.6 context.
quantize = quantize_q12_6


def _checked_int64(value: int, name: str) -> int:
    """Return ``value`` after asserting the reference's signed int64 bound."""

    if value < _INT64_MIN or value > _INT64_MAX:
        raise OverflowError(f"{name} exceeds signed int64 range: {value}")
    return int(value)


def _nested_ints(value: Sequence[Sequence[int]], rows: int, columns: int, name: str) -> IntMatrix:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a {rows}x{columns} integer matrix")
    if len(value) != rows:
        raise ValueError(f"{name} must have {rows} rows, got {len(value)}")
    result: IntMatrix = []
    for row_index, row in enumerate(value):
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            raise TypeError(f"{name}[{row_index}] must be a sequence")
        if len(row) != columns:
            raise ValueError(
                f"{name}[{row_index}] must have {columns} columns, got {len(row)}"
            )
        parsed_row: list[int] = []
        for column_index, item in enumerate(row):
            if not isinstance(item, Integral) or isinstance(item, bool):
                raise TypeError(f"{name}[{row_index}][{column_index}] must be an integer")
            item = int(item)
            if item < MIN_Q or item > MAX_Q:
                raise ValueError(
                    f"{name}[{row_index}][{column_index}]={item} is outside "
                    f"Q12.6 range [{MIN_Q}, {MAX_Q}]"
                )
            parsed_row.append(item)
        result.append(parsed_row)
    return result


def _vector_ints(value: Sequence[int], length: int, name: str) -> IntVector:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be an integer vector")
    if len(value) != length:
        raise ValueError(f"{name} must have length {length}, got {len(value)}")
    result: list[int] = []
    for index, item in enumerate(value):
        if not isinstance(item, Integral) or isinstance(item, bool):
            raise TypeError(f"{name}[{index}] must be an integer")
        item = int(item)
        if item < MIN_Q or item > MAX_Q:
            raise ValueError(
                f"{name}[{index}]={item} is outside Q12.6 range [{MIN_Q}, {MAX_Q}]"
            )
        result.append(item)
    return result


def channel_major_to_time_major(
    feature_current_q: Sequence[Sequence[int]],
) -> IntMatrix:
    """Transpose canonical software ``[32][48]`` input to HLS ``[48][32]``.

    The software model stores one row per feature channel and one column per
    time step.  The HLS contract is time-major, so this helper is the single
    explicit layout boundary used by callers before invoking the integer
    reference.  Values are validated as external Q12.6 integers.
    """

    canonical = _nested_ints(
        feature_current_q,
        FEATURE_CHANNELS,
        TIME_STEPS,
        "feature_current_q_channel_major",
    )
    return [
        [canonical[channel][time_index] for channel in range(FEATURE_CHANNELS)]
        for time_index in range(TIME_STEPS)
    ]


def _range_update(report: dict[str, dict[str, int]], name: str, value: int) -> None:
    value = _checked_int64(value, name)
    if name not in report:
        report[name] = {"min": value, "max": value}
    else:
        report[name]["min"] = min(report[name]["min"], value)
        report[name]["max"] = max(report[name]["max"], value)


def run_q12_6_reference(
    feature_current_q: Sequence[Sequence[int]],
    weight_q: Sequence[Sequence[int]],
    bias_q: Sequence[int],
    *,
    beta_q: int = BETA_Q,
    threshold_q: int = THRESHOLD_Q,
) -> dict[str, Any]:
    """Evaluate one sample according to the frozen HLS-1 integer contract.

    ``feature_current_q`` is time-major ``[48][32]``.  Every invocation creates
    fresh membrane and count state; no state is retained between calls.
    """

    if beta_q != BETA_Q or threshold_q != THRESHOLD_Q:
        raise ValueError(f"HLS-1 constants are beta_q={BETA_Q}, threshold_q={THRESHOLD_Q}")
    currents = _nested_ints(feature_current_q, TIME_STEPS, FEATURE_CHANNELS, "feature_current_q")
    weights = _nested_ints(weight_q, NUM_CLASSES, FEATURE_CHANNELS, "weight_q")
    biases = _vector_ints(bias_q, NUM_CLASSES, "bias_q")

    membrane = [0] * FEATURE_CHANNELS
    spike_count = [0] * FEATURE_CHANNELS
    spikes: IntMatrix = []
    membrane_after_reset: IntMatrix = []
    ranges: dict[str, dict[str, int]] = {}
    for value in membrane:
        _range_update(ranges, "membrane_after_reset_q", value)
    for time_index in range(TIME_STEPS):
        step_spikes: list[int] = []
        step_membrane: list[int] = []
        for channel in range(FEATURE_CHANNELS):
            beta_product = _checked_int64(BETA_Q * membrane[channel], "beta_product_q2")
            _range_update(ranges, "beta_product_q2", beta_product)
            decayed = _checked_int64(
                round_half_even_div(beta_product, SCALE), "decayed_membrane_q"
            )
            _range_update(ranges, "decayed_membrane_q", decayed)
            updated = _checked_int64(
                decayed + currents[time_index][channel], "membrane_before_reset_q"
            )
            _range_update(ranges, "membrane_before_reset_q", updated)
            spike = int(updated >= THRESHOLD_Q)
            if spike:
                updated = _checked_int64(updated - THRESHOLD_Q, "membrane_after_reset_q")
                spike_count[channel] += 1
            step_spikes.append(spike)
            step_membrane.append(updated)
            membrane[channel] = updated
            _range_update(ranges, "membrane_after_reset_q", updated)
        spikes.append(step_spikes)
        membrane_after_reset.append(step_membrane)

    rate_q = []
    for count in spike_count:
        rate = _checked_int64(round_half_even_div(count * SCALE, TIME_STEPS), "rate_q")
        rate_q.append(rate)
        _range_update(ranges, "rate_q", rate)
        _range_update(ranges, "spike_count", count)

    logits_q = []
    for class_index in range(NUM_CLASSES):
        accumulator = 0
        for channel in range(FEATURE_CHANNELS):
            product = _checked_int64(
                rate_q[channel] * weights[class_index][channel], "classifier_product_q2"
            )
            accumulator = _checked_int64(
                accumulator + product, "classifier_accumulator_q2"
            )
            _range_update(ranges, "classifier_product_q2", product)
            _range_update(ranges, "classifier_accumulator_q2", accumulator)
        logit = _checked_int64(
            round_half_even_div(accumulator, SCALE) + biases[class_index], "logits_q"
        )
        logits_q.append(logit)
        _range_update(ranges, "logits_q", logit)

    return {
        "feature_current_q": currents,
        "weight_q": weights,
        "bias_q": biases,
        "beta_q": BETA_Q,
        "threshold_q": THRESHOLD_Q,
        "spikes": spikes,
        "membrane_after_reset": membrane_after_reset,
        "spike_count": spike_count,
        "rate_q": rate_q,
        "logits_q": logits_q,
        # These values are useful for inspecting this synthetic case only;
        # they are deliberately not presented as domain-wide width bounds.
        "range_report": ranges,
        "range_report_scope": RANGE_REPORT_SCOPE,
    }


def contract_worst_case_bounds() -> dict[str, dict[str, int]]:
    """Return safe intermediate bounds for the complete accepted Q12.6 domain.

    These bounds cover arbitrary valid current, weight, and bias matrices with
    the frozen 48-step/32-channel dimensions.  They are conservative analytic
    bounds (not measurements from the checked-in synthetic vectors) and are the
    required source for HLS-2 integer-width selection.
    """

    beta_product_min = BETA_Q * _MEMBRANE_MIN_Q
    beta_product_max = BETA_Q * _MEMBRANE_MAX_Q
    decayed_min = round_half_even_div(beta_product_min, SCALE)
    decayed_max = round_half_even_div(beta_product_max, SCALE)
    membrane_before_min = decayed_min + MIN_Q
    membrane_before_max = decayed_max + MAX_Q
    rate_min = round_half_even_div(0, TIME_STEPS)
    rate_max = round_half_even_div(TIME_STEPS * SCALE, TIME_STEPS)
    classifier_product_min = rate_max * MIN_Q
    classifier_product_max = rate_max * MAX_Q
    accumulator_min = FEATURE_CHANNELS * classifier_product_min
    accumulator_max = FEATURE_CHANNELS * classifier_product_max
    logits_min = round_half_even_div(accumulator_min, SCALE) + MIN_Q
    logits_max = round_half_even_div(accumulator_max, SCALE) + MAX_Q

    return {
        "feature_current_q": {"min": MIN_Q, "max": MAX_Q},
        "beta_product_q2": {"min": beta_product_min, "max": beta_product_max},
        "decayed_membrane_q": {"min": decayed_min, "max": decayed_max},
        "membrane_before_reset_q": {
            "min": membrane_before_min,
            "max": membrane_before_max,
        },
        "membrane_after_reset_q": {
            "min": _MEMBRANE_MIN_Q,
            "max": _MEMBRANE_MAX_Q,
        },
        "spike_count": {"min": 0, "max": TIME_STEPS},
        "rate_q": {"min": rate_min, "max": rate_max},
        "classifier_product_q2": {
            "min": classifier_product_min,
            "max": classifier_product_max,
        },
        "classifier_accumulator_q2": {
            "min": accumulator_min,
            "max": accumulator_max,
        },
        "logits_q": {"min": logits_min, "max": logits_max},
    }


# Descriptive aliases keep the reference easy to discover without introducing
# another implementation or changing the historical fixed_lif_head function.
simulate_hybrid_lif_head = run_q12_6_reference
hls_lif_head = run_q12_6_reference


def contract_metadata() -> dict[str, Any]:
    """Return JSON-compatible metadata describing the executable contract."""

    return {
        "schema_version": SCHEMA_VERSION,
        "contract": "q12_6_direct_current_subtract_reset_lif",
        "rounding": "round_half_even",
        "internal_arithmetic": "signed_int64_checked_no_wrap_no_saturation",
        "input_layout": "time_major_[48][32]",
        "scale": SCALE,
        "min_q": MIN_Q,
        "max_q": MAX_Q,
        "time_steps": TIME_STEPS,
        "feature_channels": FEATURE_CHANNELS,
        "classes": NUM_CLASSES,
        "beta_q": BETA_Q,
        "threshold_q": THRESHOLD_Q,
        "range_report_scope": RANGE_REPORT_SCOPE,
        "contract_domain_bounds": contract_worst_case_bounds(),
        "contract_domain_bounds_scope": "mathematically_justified_safe_bound",
    }

