#include "hybrid_lif_head.hpp"

rounding_t round_half_even_div(rounding_t numerator, unsigned denominator) {
    const bool negative = numerator < 0;
    const rounding_t signed_magnitude = negative ? rounding_t(-numerator) : numerator;
    const magnitude_t magnitude = magnitude_t(signed_magnitude);
    magnitude_t quotient = magnitude / denominator;
    const magnitude_t remainder = magnitude % denominator;
    const magnitude_t twice_remainder = remainder * 2;

    if ((twice_remainder > denominator) ||
        ((twice_remainder == denominator) && ((quotient & 1) != 0))) {
        quotient = quotient + 1;
    }

    const rounding_t rounded = rounding_t(quotient);
    return negative ? rounding_t(-rounded) : rounded;
}

static void run_hybrid_lif_head(
    const q12_t feature_current_q[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS],
    const q12_t weight_q[HLS_NUM_CLASSES][HLS_FEATURE_CHANNELS],
    const q12_t bias_q[HLS_NUM_CLASSES],
    logits_t logits_q[HLS_NUM_CLASSES],
    count_t spike_count_q[HLS_FEATURE_CHANNELS],
    spike_t spikes[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS],
    membrane_t membrane_after_reset[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS]
) {
    membrane_t membrane[HLS_FEATURE_CHANNELS];

    for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
        membrane[channel] = 0;
        spike_count_q[channel] = 0;
    }

    for (int time_index = 0; time_index < HLS_TIME_STEPS; ++time_index) {
        for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
            const beta_product_t beta_product =
                beta_product_t(HLS_BETA_Q) * beta_product_t(membrane[channel]);
            const rounding_t decayed =
                round_half_even_div(rounding_t(beta_product), HLS_SCALE);
            membrane_t updated = membrane_t(
                decayed + rounding_t(feature_current_q[time_index][channel]));
            spike_t spike = 0;

            if (updated >= HLS_THRESHOLD_Q) {
                updated = membrane_t(updated - HLS_THRESHOLD_Q);
                spike = 1;
                spike_count_q[channel] = count_t(spike_count_q[channel] + 1);
            }

            membrane[channel] = updated;
            spikes[time_index][channel] = spike;
            membrane_after_reset[time_index][channel] = updated;
        }
    }

    rate_t rate_q[HLS_FEATURE_CHANNELS];
    for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
        const rounding_t rate_numerator =
            rounding_t(spike_count_q[channel]) * HLS_SCALE;
        rate_q[channel] = rate_t(
            round_half_even_div(rate_numerator, HLS_TIME_STEPS));
    }

    for (int class_index = 0; class_index < HLS_NUM_CLASSES; ++class_index) {
        classifier_accumulator_t accumulator = 0;
        for (int channel = 0; channel < HLS_FEATURE_CHANNELS; ++channel) {
            const classifier_product_t product =
                classifier_product_t(rate_q[channel]) *
                classifier_product_t(weight_q[class_index][channel]);
            accumulator = classifier_accumulator_t(accumulator + product);
        }

        const rounding_t scaled = round_half_even_div(
            rounding_t(accumulator), HLS_SCALE);
        logits_q[class_index] = logits_t(
            scaled + rounding_t(bias_q[class_index]));
    }
}

void hybrid_lif_head_q12_6(
    const q12_t feature_current_q[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS],
    const q12_t weight_q[HLS_NUM_CLASSES][HLS_FEATURE_CHANNELS],
    const q12_t bias_q[HLS_NUM_CLASSES],
    logits_t logits_q[HLS_NUM_CLASSES],
    count_t spike_count_q[HLS_FEATURE_CHANNELS]
) {
    spike_t spikes[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS];
    membrane_t membrane_after_reset[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS];
    run_hybrid_lif_head(
        feature_current_q, weight_q, bias_q, logits_q, spike_count_q,
        spikes, membrane_after_reset);
}

void hybrid_lif_head_q12_6_debug(
    const q12_t feature_current_q[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS],
    const q12_t weight_q[HLS_NUM_CLASSES][HLS_FEATURE_CHANNELS],
    const q12_t bias_q[HLS_NUM_CLASSES],
    logits_t logits_q[HLS_NUM_CLASSES],
    count_t spike_count_q[HLS_FEATURE_CHANNELS],
    spike_t spikes[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS],
    membrane_t membrane_after_reset[HLS_TIME_STEPS][HLS_FEATURE_CHANNELS]
) {
    run_hybrid_lif_head(
        feature_current_q, weight_q, bias_q, logits_q, spike_count_q,
        spikes, membrane_after_reset);
}
