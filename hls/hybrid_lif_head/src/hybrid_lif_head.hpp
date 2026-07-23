#ifndef HYBRID_LIF_HEAD_HPP
#define HYBRID_LIF_HEAD_HPP

#include <ap_int.h>

constexpr int HLS_TIME_STEPS = 48;
constexpr int HLS_FEATURE_CHANNELS = 32;
constexpr int HLS_NUM_CLASSES = 2;
constexpr int HLS_SCALE = 64;
constexpr int HLS_BETA_Q = 58;
constexpr int HLS_THRESHOLD_Q = 32;

typedef ap_int<12> q12_t;
typedef ap_int<16> membrane_t;
typedef ap_int<22> beta_product_t;
typedef ap_uint<1> spike_t;
typedef ap_uint<6> count_t;
typedef ap_uint<8> rate_t;
typedef ap_int<18> classifier_product_t;
typedef ap_int<23> classifier_accumulator_t;
typedef ap_int<18> logits_t;

// Wider helper types keep positive-magnitude division and intermediate sums
// explicit. The accepted contract domain is much smaller than these widths.
typedef ap_int<32> rounding_t;
typedef ap_uint<32> magnitude_t;

rounding_t round_half_even_div(rounding_t numerator, unsigned denominator);

void hybrid_lif_head_q12_6(
    const q12_t feature_current_q[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS],
    const q12_t weight_q[HLS_NUM_CLASSES][HLS_FEATURE_CHANNELS],
    const q12_t bias_q[HLS_NUM_CLASSES],
    logits_t logits_q[HLS_NUM_CLASSES],
    count_t spike_count_q[HLS_FEATURE_CHANNELS]
);

// Verification companion: exposes the per-step values while sharing the exact
// arithmetic implementation used by the HLS top function.
void hybrid_lif_head_q12_6_debug(
    const q12_t feature_current_q[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS],
    const q12_t weight_q[HLS_NUM_CLASSES][HLS_FEATURE_CHANNELS],
    const q12_t bias_q[HLS_NUM_CLASSES],
    logits_t logits_q[HLS_NUM_CLASSES],
    count_t spike_count_q[HLS_FEATURE_CHANNELS],
    spike_t spikes[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS],
    membrane_t membrane_after_reset[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS]
);

#endif
