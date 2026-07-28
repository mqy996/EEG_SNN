#include <stdint.h>
#include "xil_printf.h"
#include "snn_replay_regs.h"
#include "golden_vectors_q12_6.h"

#define SNN_REPLAY_VERSION_VALUE 0x00010001U
#define SNN_REPLAY_TIMEOUT 20000000U

static uint32_t q12_6_word(int16_t value) {
    return ((uint32_t)value) & 0x0FFFU;
}

static int32_t sign_extend_18(uint32_t value) {
    value &= 0x3FFFFU;
    if ((value & 0x20000U) != 0U) {
        value |= 0xFFFC0000U;
    }
    return (int32_t)value;
}

static uint32_t expected_checksum(const snn_golden_case_t *vector) {
    uint32_t checksum = 0U;
    uint32_t i;
    for (i = 0U; i < SNN_GOLDEN_FEATURE_WORDS; ++i) {
        checksum ^= q12_6_word(vector->feature_current_q[i]);
    }
    for (i = 0U; i < SNN_GOLDEN_WEIGHT_WORDS; ++i) {
        checksum ^= q12_6_word(vector->weight_q[i]);
    }
    for (i = 0U; i < SNN_GOLDEN_BIAS_WORDS; ++i) {
        checksum ^= q12_6_word(vector->bias_q[i]);
    }
    return checksum;
}

static void load_vector(const snn_golden_case_t *vector) {
    uint32_t i;
    xil_printf("AXI_FIRST_FEATURE_WRITE index=0 data=0x%08x\r\n",
               q12_6_word(vector->feature_current_q[0]));
    for (i = 0U; i < SNN_GOLDEN_FEATURE_WORDS; ++i) {
        snn_replay_write(SNN_REPLAY_FEATURE_INDEX, i);
        snn_replay_write(SNN_REPLAY_FEATURE_DATA, q12_6_word(vector->feature_current_q[i]));
    }
    for (i = 0U; i < SNN_GOLDEN_WEIGHT_WORDS; ++i) {
        snn_replay_write(SNN_REPLAY_WEIGHT_INDEX, i);
        snn_replay_write(SNN_REPLAY_WEIGHT_DATA, q12_6_word(vector->weight_q[i]));
    }
    for (i = 0U; i < SNN_GOLDEN_BIAS_WORDS; ++i) {
        snn_replay_write(SNN_REPLAY_BIAS_INDEX, i);
        snn_replay_write(SNN_REPLAY_BIAS_DATA, q12_6_word(vector->bias_q[i]));
    }
}

static int run_vector(uint32_t vector_id, const snn_golden_case_t *vector) {
    uint32_t status = 0U;
    uint32_t error_status = 0U;
    uint32_t checksum;
    uint32_t poll_count = 0U;
    uint32_t i;
    int failures = 0;

    xil_printf("CASE_BEGIN id=%d name=%s\r\n", vector_id, vector->name);
    xil_printf("AXI_RESET_SENT\r\n");
    snn_replay_write(SNN_REPLAY_CONTROL, SNN_REPLAY_CONTROL_SOFT_RESET);
    status = snn_replay_read(SNN_REPLAY_STATUS);
    xil_printf("RESET_STATUS=0x%08x\r\n", status);

    snn_replay_write(SNN_REPLAY_VECTOR_ID, vector_id);
    load_vector(vector);
    checksum = snn_replay_read(SNN_REPLAY_CHECKSUM);
    xil_printf("CHECKSUM hw=0x%08x expected=0x%08x\r\n",
               checksum, expected_checksum(vector));
    if (checksum != expected_checksum(vector)) {
        xil_printf("VECTOR=%s CHECKSUM_FAIL hw=0x%08x sw=0x%08x\r\n",
                   vector->name, checksum, expected_checksum(vector));
        snn_replay_write(SNN_REPLAY_CONTROL, SNN_REPLAY_CONTROL_CLEAR_DONE);
        return 1;
    }

    xil_printf("AXI_START_SENT\r\n");
    snn_replay_write(SNN_REPLAY_CONTROL, SNN_REPLAY_CONTROL_START);
    for (poll_count = 0U; poll_count < SNN_REPLAY_TIMEOUT; ++poll_count) {
        status = snn_replay_read(SNN_REPLAY_STATUS);
        if ((status & SNN_REPLAY_STATUS_DONE) != 0U) {
            break;
        }
    }
    if ((status & SNN_REPLAY_STATUS_DONE) == 0U) {
        xil_printf("VECTOR=%s TIMEOUT status=0x%08x polls=%d\r\n",
                   vector->name, status, poll_count);
        snn_replay_write(SNN_REPLAY_CONTROL, SNN_REPLAY_CONTROL_CLEAR_DONE);
        return 1;
    }

    error_status = snn_replay_read(SNN_REPLAY_ERROR_STATUS);
    xil_printf("DONE status=0x%08x polls=%d error=0x%08x\r\n",
               status, poll_count, error_status);
    if (error_status != 0U) {
        xil_printf("VECTOR=%s HW_ERROR=0x%08x\r\n", vector->name, error_status);
        snn_replay_write(SNN_REPLAY_CONTROL, SNN_REPLAY_CONTROL_CLEAR_DONE);
        return 1;
    }

    xil_printf("LOGITS expected=%d,%d actual=", vector->expected_logits_q[0],
               vector->expected_logits_q[1]);
    for (i = 0U; i < SNN_GOLDEN_LOGIT_WORDS; ++i) {
        uint32_t raw;
        int32_t actual;
        snn_replay_write(SNN_REPLAY_LOGIT_INDEX, i);
        raw = snn_replay_read(SNN_REPLAY_LOGIT_DATA);
        actual = sign_extend_18(raw);
        xil_printf("%s%d", i == 0U ? "" : ",", actual);
        if (actual != vector->expected_logits_q[i]) {
            failures = 1;
        }
    }
    xil_printf("\r\n");

    xil_printf("COUNTS expected=");
    for (i = 0U; i < SNN_GOLDEN_COUNT_WORDS; ++i) {
        xil_printf("%s%d", i == 0U ? "" : ",", vector->expected_counts[i]);
    }
    xil_printf(" actual=");
    for (i = 0U; i < SNN_GOLDEN_COUNT_WORDS; ++i) {
        uint32_t actual;
        snn_replay_write(SNN_REPLAY_COUNT_INDEX, i);
        actual = snn_replay_read(SNN_REPLAY_COUNT_DATA) & 0x3FU;
        xil_printf("%s%d", i == 0U ? "" : ",", actual);
        if (actual != (uint32_t)vector->expected_counts[i]) {
            failures = 1;
        }
    }
    xil_printf("\r\n");

    snn_replay_write(SNN_REPLAY_CONTROL, SNN_REPLAY_CONTROL_CLEAR_DONE);
    xil_printf("AXI_CLEAR_DONE_SENT\r\n");
    xil_printf("VECTOR=%s %s checksum=0x%08x status=0x%08x polls=%d error=0x%08x\r\n",
               vector->name, failures == 0 ? "PASS" : "FAIL", checksum, status,
               poll_count, error_status);
    return failures;
}

int main(void) {
    uint32_t version;
    uint32_t i;
    int failures = 0;

    xil_printf("SNN standalone replay start\r\n");
    xil_printf("AXI_PROBE=VERSION_BEGIN base=0x%08x\r\n", SNN_REPLAY_BASEADDR);
    version = snn_replay_read(SNN_REPLAY_VERSION);
    xil_printf("BASE=0x%08x VERSION=0x%08x JSON_SHA256=%s\r\n",
               SNN_REPLAY_BASEADDR, version, SNN_GOLDEN_JSON_SHA256);
    if (version != SNN_REPLAY_VERSION_VALUE) {
        xil_printf("VERSION_FAIL expected=0x%08x actual=0x%08x\r\n",
                   SNN_REPLAY_VERSION_VALUE, version);
        return 1;
    }
    xil_printf("VERSION_PASS\r\n");
    for (i = 0U; i < SNN_GOLDEN_CASE_COUNT; ++i) {
        failures |= run_vector(i, &snn_golden_cases[i]);
    }
    xil_printf("SNN standalone replay %s cases=%d\r\n",
               failures == 0 ? "PASS" : "FAIL", SNN_GOLDEN_CASE_COUNT);
    return failures == 0 ? 0 : 1;
}
