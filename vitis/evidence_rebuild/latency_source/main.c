#include <stdint.h>

#include "xparameters.h"
#include "xil_io.h"
#include "xil_printf.h"
#include "xil_types.h"
#include "xiltimer.h"
#include "sleep.h"
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


static uint32_t ticks_to_us(XTime ticks) {
    return (uint32_t)((ticks * 1000000ULL) / COUNTS_PER_SECOND);
}

static int timer_self_check(void) {
    XTime t0;
    XTime t1;

    (void)XilSleepTimer_Init(&TimerInst);
    usleep(1);
    XTime_GetTime(&t0);
    usleep(1);
    XTime_GetTime(&t1);
    if (t1 <= t0) {
        xil_printf("TIMER_START_RESULT=FAIL\r\n");
        return 1;
    }
    xil_printf("TIMER_START_RESULT=PASS\r\n");
    return 0;
}

static int run_vector_timed(uint32_t vector_id,
                            const snn_multisample_vector_t *vector,
                            uint32_t *axil_us,
                            uint32_t *compute_us,
                            uint32_t *total_us,
                            uint32_t *polls_out) {
    uint32_t status;
    uint32_t checksum;
    uint32_t error_status;
    uint32_t polls;
    uint32_t i;
    int failures = 0;
    XTime t_total_start;
    XTime t_load_start;
    XTime t_compute_start;
    XTime t_done;

    XTime_GetTime(&t_total_start);
    write_reg(SNN_CONTROL_OFFSET, SNN_CONTROL_SOFT_RESET);
    status = read_reg(SNN_STATUS_OFFSET);
    if ((status & SNN_STATUS_IDLE) == 0U) {
        xil_printf("CASE_RESULT=FAIL id=%u stage=reset status=0x%08x\r\n", vector_id, status);
        return 1;
    }

    XTime_GetTime(&t_load_start);
    write_reg(SNN_VECTOR_ID_OFFSET, vector_id);
    load_vector(vector);
    checksum = read_reg(SNN_CHECKSUM_OFFSET);
    if (checksum != vector->checksum || checksum != expected_checksum(vector)) {
        xil_printf("CASE_RESULT=FAIL id=%u stage=checksum hw=0x%08x expected=0x%08x\r\n",
                   vector_id, checksum, vector->checksum);
        write_reg(SNN_CONTROL_OFFSET, SNN_CONTROL_CLEAR_DONE);
        return 1;
    }

    XTime_GetTime(&t_compute_start);
    write_reg(SNN_CONTROL_OFFSET, SNN_CONTROL_START);
    for (polls = 0U; polls < SNN_REPLAY_TIMEOUT; ++polls) {
        status = read_reg(SNN_STATUS_OFFSET);
        if ((status & SNN_STATUS_DONE) != 0U) {
            break;
        }
    }
    XTime_GetTime(&t_done);
    error_status = read_reg(SNN_ERROR_STATUS_OFFSET);
    if ((status & SNN_STATUS_DONE) == 0U || error_status != 0U) {
        xil_printf("CASE_RESULT=FAIL id=%u stage=done status=0x%08x error=0x%08x\r\n",
                   vector_id, status, error_status);
        write_reg(SNN_CONTROL_OFFSET, SNN_CONTROL_CLEAR_DONE);
        return 1;
    }

    for (i = 0U; i < 2U; ++i) {
        int32_t actual;
        write_reg(SNN_LOGIT_INDEX_OFFSET, i);
        actual = sign_extend_18(read_reg(SNN_LOGIT_DATA_OFFSET));
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

    *axil_us = ticks_to_us(t_compute_start - t_load_start);
    *compute_us = ticks_to_us(t_done - t_compute_start);
    *total_us = ticks_to_us(t_done - t_total_start);
    *polls_out = polls;
    xil_printf("LATENCY_SAMPLE id=%u axil_us=%u compute_us=%u total_us=%u polls=%u\r\n",
               vector_id, *axil_us, *compute_us, *total_us, polls);
    xil_printf("CASE_RESULT=%s id=%u checksum=0x%08x\r\n",
               failures == 0 ? "PASS" : "FAIL", vector_id, checksum);
    return failures;
}

static void print_u64_hex(const char *name, uint64_t value) {
    xil_printf("%s=0x%08x%08x", name,
               (uint32_t)(value >> 32), (uint32_t)value);
}

int main(void) {
    uint32_t version;
    uint32_t i;
    uint32_t correct = 0U;
    uint32_t axil_us;
    uint32_t compute_us;
    uint32_t total_us;
    uint32_t polls;
    uint32_t min_axil = 0xFFFFFFFFU;
    uint32_t max_axil = 0U;
    uint32_t min_compute = 0xFFFFFFFFU;
    uint32_t max_compute = 0U;
    uint32_t min_total = 0xFFFFFFFFU;
    uint32_t max_total = 0U;
    uint64_t sum_axil = 0U;
    uint64_t sum_compute = 0U;
    uint64_t sum_total = 0U;
    uint64_t sum_polls = 0U;
    int failures = 0;

    xil_printf("SNN_LATENCY_THROUGHPUT_START\r\n");
    xil_printf("SNN_BASE=0x%08x CASES=%u\r\n", (unsigned)SNN_BASEADDR, SNN_MULTISAMPLE_COUNT);
    xil_printf("SNN_DEVICE_CONTRACT=xc7z020clg400-2 DDR=MT41J256M16_RE-125 FCLK0_HZ=50000000\r\n");
    xil_printf("SNN_TIMING_COUNTER=COUNTS_PER_SECOND=%u\r\n", (unsigned)COUNTS_PER_SECOND);
    xil_printf("SNN_TIMING_SCOPE=full_replay_reset_plus_axi_lite_load_plus_start_to_done\r\n");
    xil_printf("SNN_COMPUTE_SCOPE=start_write_to_done_status\r\n");

    version = read_reg(SNN_VERSION_OFFSET);
    xil_printf("VERSION hw=0x%08x expected=0x%08x\r\n", version, SNN_EXPECTED_VERSION);
    if (version != SNN_EXPECTED_VERSION) {
        xil_printf("SNN_LATENCY_THROUGHPUT_RESULT=FAIL stage=version\r\n");
        return 1;
    }
    if ((read_reg(SNN_STATUS_OFFSET) & SNN_STATUS_IDLE) == 0U) {
        xil_printf("SNN_LATENCY_THROUGHPUT_RESULT=FAIL stage=status\r\n");
        return 1;
    }
    if (timer_self_check() != 0) {
        xil_printf("SNN_LATENCY_THROUGHPUT_RESULT=FAIL stage=timer_start\r\n");
        return 1;
    }

    for (i = 0U; i < SNN_MULTISAMPLE_COUNT; ++i) {
        if (snn_multisample_vectors[i].predicted == snn_multisample_vectors[i].label) {
            ++correct;
        }
        if (run_vector_timed(i, &snn_multisample_vectors[i], &axil_us, &compute_us,
                             &total_us, &polls) != 0) {
            failures = 1;
        }
        if (axil_us < min_axil) min_axil = axil_us;
        if (axil_us > max_axil) max_axil = axil_us;
        if (compute_us < min_compute) min_compute = compute_us;
        if (compute_us > max_compute) max_compute = compute_us;
        if (total_us < min_total) min_total = total_us;
        if (total_us > max_total) max_total = total_us;
        sum_axil += axil_us;
        sum_compute += compute_us;
        sum_total += total_us;
        sum_polls += polls;
    }

    xil_printf("SNN_ACCURACY correct=%u total=%u percent_x100=%u\r\n",
               correct, SNN_MULTISAMPLE_COUNT,
               (correct * 10000U) / SNN_MULTISAMPLE_COUNT);
    xil_printf("SNN_LATENCY_AXIL min_us=%u max_us=%u mean_us=%u ",
               min_axil, max_axil, (uint32_t)(sum_axil / SNN_MULTISAMPLE_COUNT));
    print_u64_hex("sum_us", sum_axil);
    xil_printf("\r\n");
    xil_printf("SNN_LATENCY_COMPUTE min_us=%u max_us=%u mean_us=%u ",
               min_compute, max_compute, (uint32_t)(sum_compute / SNN_MULTISAMPLE_COUNT));
    print_u64_hex("sum_us", sum_compute);
    xil_printf("\r\n");
    xil_printf("SNN_LATENCY_TOTAL min_us=%u max_us=%u mean_us=%u ",
               min_total, max_total, (uint32_t)(sum_total / SNN_MULTISAMPLE_COUNT));
    print_u64_hex("sum_us", sum_total);
    xil_printf("\r\n");
    if (sum_total == 0U) {
        xil_printf("SNN_THROUGHPUT_FULL_REPLAY=INVALID_TIMER sum_total=0\r\n");
        xil_printf("INVALID_TIMER\r\n");
        failures = 1;
    } else {
        xil_printf("SNN_THROUGHPUT_FULL_REPLAY mean_samples_per_s_x100=%u\r\n",
                   (uint32_t)(((uint64_t)SNN_MULTISAMPLE_COUNT * 100000000ULL) / sum_total));
    }
    xil_printf("SNN_POLLING mean_polls=%u ", (uint32_t)(sum_polls / SNN_MULTISAMPLE_COUNT));
    print_u64_hex("sum_polls", sum_polls);
    xil_printf("\r\n");
    xil_printf("SNN_LATENCY_THROUGHPUT_RESULT=%s\r\n", failures == 0 ? "PASS" : "FAIL");
    return failures;
}
