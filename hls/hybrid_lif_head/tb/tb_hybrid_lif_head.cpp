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

void fail_matrix(
    const char* case_name,
    const char* field,
    int time_index,
    int channel,
    int expected,
    int actual
) {
    std::printf(
        "FAIL case=%s field=%s time=%d channel=%d expected=%d actual=%d\n",
        case_name, field, time_index, channel, expected, actual);
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

void check_outputs(
    const hls_golden::GoldenCase& golden,
    const logits_t logits_q[HLS_NUM_CLASSES],
    const count_t spike_count_q[HLS_FEATURE_CHANNELS],
    const spike_t spikes[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS],
    const membrane_t membrane_after_reset[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS]
) {
    for (int time_index = 0; time_index < HLS_TIME_STEPS; ++time_index) {
        for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
            const int actual_spike = int(spikes[time_index][channel]);
            if (actual_spike != golden.spikes[time_index][channel]) {
                fail_matrix(
                    golden.case_name, "spikes", time_index, channel,
                    golden.spikes[time_index][channel], actual_spike);
            }
            const int actual_membrane = int(membrane_after_reset[time_index][channel]);
            if (actual_membrane != golden.membrane_after_reset[time_index][channel]) {
                fail_matrix(
                    golden.case_name, "membrane_after_reset", time_index, channel,
                    golden.membrane_after_reset[time_index][channel], actual_membrane);
            }
        }
    }
    for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
        const int actual_count = int(spike_count_q[channel]);
        if (actual_count != golden.spike_count[channel]) {
            fail_scalar(
                golden.case_name, "spike_count", channel,
                golden.spike_count[channel], actual_count);
        }
    }
    for (int class_index = 0; class_index < HLS_NUM_CLASSES; ++class_index) {
        const int actual_logit = int(logits_q[class_index]);
        if (actual_logit != golden.logits_q[class_index]) {
            fail_scalar(
                golden.case_name, "logits_q", class_index,
                golden.logits_q[class_index], actual_logit);
        }
    }
}

void check_rate_from_counts(
    const hls_golden::GoldenCase& golden,
    const count_t spike_count_q[HLS_FEATURE_CHANNELS]
) {
    for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
        const rounding_t numerator = rounding_t(spike_count_q[channel]) * HLS_SCALE;
        const int actual_rate = int(round_half_even_div(numerator, HLS_TIME_STEPS));
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

    logits_t debug_logits[HLS_NUM_CLASSES];
    count_t debug_counts[HLS_FEATURE_CHANNELS];
    spike_t spikes[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS];
    membrane_t membrane_after_reset[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS];
    hybrid_lif_head_q12_6_debug(
        feature_current_q, weight_q, bias_q, debug_logits, debug_counts,
        spikes, membrane_after_reset);
    check_outputs(golden, debug_logits, debug_counts, spikes, membrane_after_reset);
    check_rate_from_counts(golden, debug_counts);

    // Exercise the declared top function and invoke it twice to prove local
    // membrane/count state is reset between calls.
    logits_t top_logits[HLS_NUM_CLASSES];
    count_t top_counts[HLS_FEATURE_CHANNELS];
    hybrid_lif_head_q12_6(
        feature_current_q, weight_q, bias_q, top_logits, top_counts);
    for (int class_index = 0; class_index < HLS_NUM_CLASSES; ++class_index) {
        if (int(top_logits[class_index]) != golden.logits_q[class_index]) {
            fail_scalar(
                golden.case_name, "top_logits_q", class_index,
                golden.logits_q[class_index], int(top_logits[class_index]));
        }
    }
    for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
        if (int(top_counts[channel]) != golden.spike_count[channel]) {
            fail_scalar(
                golden.case_name, "top_spike_count", channel,
                golden.spike_count[channel], int(top_counts[channel]));
        }
    }

    logits_t repeat_logits[HLS_NUM_CLASSES];
    count_t repeat_counts[HLS_FEATURE_CHANNELS];
    hybrid_lif_head_q12_6(
        feature_current_q, weight_q, bias_q, repeat_logits, repeat_counts);
    for (int class_index = 0; class_index < HLS_NUM_CLASSES; ++class_index) {
        if (int(repeat_logits[class_index]) != int(top_logits[class_index])) {
            fail_scalar(
                golden.case_name, "reset_logits_q", class_index,
                int(top_logits[class_index]), int(repeat_logits[class_index]));
        }
    }
    for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
        if (int(repeat_counts[channel]) != int(top_counts[channel])) {
            fail_scalar(
                golden.case_name, "reset_spike_count", channel,
                int(top_counts[channel]), int(repeat_counts[channel]));
        }
    }
}

}  // namespace

int main() {
    for (int case_index = 0; case_index < 3; ++case_index) {
        run_case(hls_golden::cases[case_index]);
    }
    if (failures != 0) {
        std::printf("HLS-2 C simulation FAIL failures=%d\n", failures);
        return 1;
    }
    std::printf("HLS-2 C simulation PASS cases=3\n");
    return 0;
}
