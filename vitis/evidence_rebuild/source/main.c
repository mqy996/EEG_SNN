#include <stdint.h>

#include "xparameters.h"
#include "xil_io.h"
#include "xil_printf.h"
#include "xil_types.h"
#include "snn_multisample_vectors.h"

#ifndef XPAR_SNN_AXI_MEMORY_WINDOW_0_BASEADDR
#error "XPAR_SNN_AXI_MEMORY_WINDOW_0_BASEADDR is missing from the selected platform"
#endif

#define SNN_BASEADDR ((UINTPTR)XPAR_SNN_AXI_MEMORY_WINDOW_0_BASEADDR)
#define SNN_CONTROL_OFFSET       0x00U
#define SNN_STATUS_OFFSET        0x04U
#define SNN_VERSION_OFFSET       0x08U
#define SNN_VECTOR_ID_OFFSET     0x0CU
#define SNN_FEATURE_INDEX_OFFSET 0x10U
#define SNN_FEATURE_DATA_OFFSET  0x14U
#define SNN_WEIGHT_INDEX_OFFSET  0x18U
#define SNN_WEIGHT_DATA_OFFSET   0x1CU
#define SNN_BIAS_INDEX_OFFSET    0x20U
#define SNN_BIAS_DATA_OFFSET     0x24U
#define SNN_LOGIT_INDEX_OFFSET   0x28U
#define SNN_LOGIT_DATA_OFFSET    0x2CU
#define SNN_COUNT_INDEX_OFFSET   0x30U
#define SNN_COUNT_DATA_OFFSET    0x34U
#define SNN_CHECKSUM_OFFSET      0x38U
#define SNN_ERROR_STATUS_OFFSET  0x3CU

#define SNN_CONTROL_START        (1U << 0)
#define SNN_CONTROL_SOFT_RESET   (1U << 1)
#define SNN_CONTROL_CLEAR_DONE   (1U << 2)
#define SNN_STATUS_IDLE          (1U << 0)
#define SNN_STATUS_DONE          (1U << 1)
#define SNN_EXPECTED_VERSION     0x00010001U
#define SNN_REPLAY_TIMEOUT       20000000U

static uint32_t read_reg(uint32_t offset) {
    return Xil_In32(SNN_BASEADDR + offset);
}

static void write_reg(uint32_t offset, uint32_t value) {
    Xil_Out32(SNN_BASEADDR + offset, value);
}

static uint32_t q12_word(int16_t value) {
    return ((uint32_t)(int32_t)value) & 0xFFFU;
}

static int32_t sign_extend_18(uint32_t value) {
    value &= 0x3FFFFU;
    if ((value & 0x20000U) != 0U) {
        value |= 0xFFFC0000U;
    }
    return (int32_t)value;
}

static uint32_t expected_checksum(const snn_multisample_vector_t *vector) {
    uint32_t checksum = 0U;
    uint32_t i;
    for (i = 0U; i < SNN_MULTISAMPLE_FEATURE_WORDS; ++i) {
        checksum ^= q12_word(vector->feature_q[i]);
    }
    for (i = 0U; i < SNN_MULTISAMPLE_WEIGHT_WORDS; ++i) {
        checksum ^= q12_word(snn_multisample_weight_q[i]);
    }
    for (i = 0U; i < SNN_MULTISAMPLE_BIAS_WORDS; ++i) {
        checksum ^= q12_word(snn_multisample_bias_q[i]);
    }
    return checksum;
}

static void load_vector(const snn_multisample_vector_t *vector) {
    uint32_t i;
    for (i = 0U; i < SNN_MULTISAMPLE_FEATURE_WORDS; ++i) {
        write_reg(SNN_FEATURE_INDEX_OFFSET, i);
        write_reg(SNN_FEATURE_DATA_OFFSET, q12_word(vector->feature_q[i]));
    }
    for (i = 0U; i < SNN_MULTISAMPLE_WEIGHT_WORDS; ++i) {
        write_reg(SNN_WEIGHT_INDEX_OFFSET, i);
        write_reg(SNN_WEIGHT_DATA_OFFSET, q12_word(snn_multisample_weight_q[i]));
    }
    for (i = 0U; i < SNN_MULTISAMPLE_BIAS_WORDS; ++i) {
        write_reg(SNN_BIAS_INDEX_OFFSET, i);
        write_reg(SNN_BIAS_DATA_OFFSET, q12_word(snn_multisample_bias_q[i]));
    }
}

static int run_vector(uint32_t vector_id, const snn_multisample_vector_t *vector) {
    uint32_t status;
    uint32_t checksum;
    uint32_t error_status;
    uint32_t polls;
    uint32_t i;
    int failures = 0;

    xil_printf("CASE_BEGIN id=%u local=%u label=%u expected=%u\r\n",
               vector_id, vector->sample_local_index, vector->label, vector->predicted);
    write_reg(SNN_CONTROL_OFFSET, SNN_CONTROL_SOFT_RESET);
    status = read_reg(SNN_STATUS_OFFSET);
    if ((status & SNN_STATUS_IDLE) == 0U) {
        xil_printf("CASE_RESULT=FAIL stage=reset status=0x%08x\r\n", status);
        return 1;
    }
    write_reg(SNN_VECTOR_ID_OFFSET, vector_id);
    load_vector(vector);

    checksum = read_reg(SNN_CHECKSUM_OFFSET);
    xil_printf("CHECKSUM hw=0x%08x expected=0x%08x\r\n", checksum, expected_checksum(vector));
    if (checksum != vector->checksum || checksum != expected_checksum(vector)) {
        xil_printf("CASE_RESULT=FAIL stage=checksum\r\n");
        write_reg(SNN_CONTROL_OFFSET, SNN_CONTROL_CLEAR_DONE);
        return 1;
    }

    write_reg(SNN_CONTROL_OFFSET, SNN_CONTROL_START);
    for (polls = 0U; polls < SNN_REPLAY_TIMEOUT; ++polls) {
        status = read_reg(SNN_STATUS_OFFSET);
        if ((status & SNN_STATUS_DONE) != 0U) {
            break;
        }
    }
    error_status = read_reg(SNN_ERROR_STATUS_OFFSET);
    if ((status & SNN_STATUS_DONE) == 0U || error_status != 0U) {
        xil_printf("CASE_RESULT=FAIL stage=done status=0x%08x error=0x%08x\r\n", status, error_status);
        write_reg(SNN_CONTROL_OFFSET, SNN_CONTROL_CLEAR_DONE);
        return 1;
    }

    for (i = 0U; i < 2U; ++i) {
        int32_t actual;
        write_reg(SNN_LOGIT_INDEX_OFFSET, i);
        actual = sign_extend_18(read_reg(SNN_LOGIT_DATA_OFFSET));
        xil_printf("LOGIT index=%u actual=%d expected=%d\r\n", i, actual, vector->expected_logits_q[i]);
        if (actual != vector->expected_logits_q[i]) {
            failures = 1;
        }
    }
    for (i = 0U; i < SNN_MULTISAMPLE_COUNT_WORDS; ++i) {
        uint32_t actual;
        write_reg(SNN_COUNT_INDEX_OFFSET, i);
        actual = read_reg(SNN_COUNT_DATA_OFFSET) & 0x3FU;
        if (actual != (uint32_t)vector->expected_counts[i]) {
            failures = 1;
        }
    }
    write_reg(SNN_CONTROL_OFFSET, SNN_CONTROL_CLEAR_DONE);
    xil_printf("CASE_RESULT=%s checksum=0x%08x polls=%u\r\n",
               failures == 0 ? "PASS" : "FAIL", checksum, polls);
    return failures;
}

int main(void) {
    uint32_t version;
    uint32_t i;

    xil_printf("SNN_BEST_FOLD9_REPLAY_START\r\n");
    xil_printf("SNN_BASE=0x%08x CASES=%u\r\n", (unsigned)SNN_BASEADDR, SNN_MULTISAMPLE_COUNT);
    xil_printf("SNN_MODEL=S2_HLS_MATCHED_BEST_HELDOUT_FOLD9\r\n");
    xil_printf("SNN_SOFTWARE_ACCURACY=0.882166\r\n");
    xil_printf("SNN_SOFTWARE_MACRO_F1=0.881963\r\n");
    xil_printf("SNN_HLS_CONTRACT=Q12.6 beta_q=58 threshold_q=32\r\n");
    version = read_reg(SNN_VERSION_OFFSET);
    xil_printf("VERSION hw=0x%08x expected=0x%08x\r\n", version, SNN_EXPECTED_VERSION);
    if (version != SNN_EXPECTED_VERSION) {
        xil_printf("SNN_BEST_FOLD9_REPLAY_RESULT=FAIL stage=version\r\n");
        return 1;
    }
    if ((read_reg(SNN_STATUS_OFFSET) & SNN_STATUS_IDLE) == 0U) {
        xil_printf("SNN_BEST_FOLD9_REPLAY_RESULT=FAIL stage=status\r\n");
        return 1;
    }
    for (i = 0U; i < SNN_MULTISAMPLE_COUNT; ++i) {
        if (run_vector(i, &snn_multisample_vectors[i]) != 0) {
            xil_printf("SNN_BEST_FOLD9_REPLAY_RESULT=FAIL vector=%u\r\n", i);
            return 1;
        }
    }
    xil_printf("SNN_BEST_FOLD9_REPLAY_RESULT=PASS\r\n");
    return 0;
}
