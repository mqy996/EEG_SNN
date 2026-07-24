#include <cstdio>

#include "../src/hybrid_lif_head.hpp"
#include "golden_vectors_q12_6.hpp"

namespace {

int failures = 0;

void fail_scalar(const char* case_name, const char* field, int index, int expected, int actual) {
    std::printf(
        "FAIL case=%s field=%s index=%d expected=%d actual=%d\n",
        case_name, field, index, expected, actual);
    ++failures;
}

void load_case(
    const hls_golden::GoldenCase& golden,
    q12_t feature_current_q[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS],
    q12_t weight_q[HLS_NUM_CLASSES][HLS_FEATURE_CHANNELS],
    q12_t bias_q[HLS_NUM_CLASSES]
) {
    for (int time_index = 0; time_index < HLS_TIME_STEPS; ++time_index) {
        for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
            feature_current_q[time_index][channel] =
                q12_t(golden.feature_current_q[time_index][channel]);
        }
    }
    for (int class_index = 0; class_index < HLS_NUM_CLASSES; ++class_index) {
        bias_q[class_index] = q12_t(golden.bias_q[class_index]);
        for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
            weight_q[class_index][channel] =
                q12_t(golden.weight_q[class_index][channel]);
        }
    }
}

void check_top_outputs(
    const hls_golden::GoldenCase& golden,
    const logits_t logits_q[HLS_NUM_CLASSES],
    const count_t spike_count_q[HLS_FEATURE_CHANNELS],
    const char* suffix
) {
    for (int class_index = 0; class_index < HLS_NUM_CLASSES; ++class_index) {
        const int actual = int(logits_q[class_index]);
        if (actual != golden.logits_q[class_index]) {
            fail_scalar(
                golden.case_name, suffix, class_index,
                golden.logits_q[class_index], actual);
        }
    }
    for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
        const int actual = int(spike_count_q[channel]);
        if (actual != golden.spike_count[channel]) {
            fail_scalar(
                golden.case_name, suffix, channel,
                golden.spike_count[channel], actual);
        }
    }
}

void check_rate_from_counts(
    const hls_golden::GoldenCase& golden,
    const count_t spike_count_q[HLS_FEATURE_CHANNELS]
) {
    for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
        const rounding_t numerator =
            rounding_t(spike_count_q[channel]) * HLS_SCALE;
        const int actual_rate =
            int(round_half_even_div(numerator, HLS_TIME_STEPS));
        if (actual_rate != golden.rate_q[channel]) {
            fail_scalar(
                golden.case_name, "rate_q", channel,
                golden.rate_q[channel], actual_rate);
        }
    }
}

void run_case(const hls_golden::GoldenCase& golden) {
    q12_t feature_current_q[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS];
    q12_t weight_q[HLS_NUM_CLASSES][HLS_FEATURE_CHANNELS];
    q12_t bias_q[HLS_NUM_CLASSES];
    load_case(golden, feature_current_q, weight_q, bias_q);

    logits_t logits_q[HLS_NUM_CLASSES];
    count_t spike_count_q[HLS_FEATURE_CHANNELS];
    hybrid_lif_head_q12_6(
        feature_current_q, weight_q, bias_q, logits_q, spike_count_q);
    check_top_outputs(golden, logits_q, spike_count_q, "top_output");
    check_rate_from_counts(golden, spike_count_q);

    // Repeat the same top call to verify call-level state reset in RTL.
    logits_t repeat_logits_q[HLS_NUM_CLASSES];
    count_t repeat_spike_count_q[HLS_FEATURE_CHANNELS];
    hybrid_lif_head_q12_6(
        feature_current_q, weight_q, bias_q,
        repeat_logits_q, repeat_spike_count_q);
    check_top_outputs(
        golden, repeat_logits_q, repeat_spike_count_q, "reset_output");
}

}  // namespace

int main() {
    for (int case_index = 0; case_index < 3; ++case_index) {
        run_case(hls_golden::cases[case_index]);
    }
    if (failures != 0) {
        std::printf(
            "HLS-4 C/RTL co-simulation FAIL failures=%d\n", failures);
        return 1;
    }
    std::printf("HLS-4 C/RTL co-simulation PASS cases=3\n");
    return 0;
}
