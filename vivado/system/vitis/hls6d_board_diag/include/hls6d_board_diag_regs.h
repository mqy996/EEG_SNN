#ifndef HLS6D_BOARD_DIAG_REGS_H
#define HLS6D_BOARD_DIAG_REGS_H

#include <stdint.h>
#include "xil_io.h"

#define HLS6D_AXI_GPIO_BASEADDR 0x41200000U
#define HLS6D_SNN_BASEADDR      0x43C00000U
#define HLS6D_SNN_STATUS_OFFSET 0x04U
#define HLS6D_SNN_VERSION_OFFSET 0x08U
#define HLS6D_SNN_VERSION_VALUE 0x00010001U

static inline uint32_t hls6d_gpio_read(void) {
    return Xil_In32(HLS6D_AXI_GPIO_BASEADDR);
}

static inline uint32_t hls6d_snn_version_read(void) {
    return Xil_In32(HLS6D_SNN_BASEADDR + HLS6D_SNN_VERSION_OFFSET);
}

static inline uint32_t hls6d_snn_status_read(void) {
    return Xil_In32(HLS6D_SNN_BASEADDR + HLS6D_SNN_STATUS_OFFSET);
}

#endif /* HLS6D_BOARD_DIAG_REGS_H */
