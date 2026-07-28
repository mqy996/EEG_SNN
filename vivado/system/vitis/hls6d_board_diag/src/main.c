#include <stdint.h>

#include "hls6d_board_diag_regs.h"
#include "xil_printf.h"

int main(void) {
    uint32_t gpio_value;
    uint32_t version_value;
    uint32_t status_value;

    xil_printf("HLS6D_DIAG_START\r\n");

    xil_printf("GPIO_READ_BEGIN addr=0x%08x\r\n", HLS6D_AXI_GPIO_BASEADDR);
    gpio_value = hls6d_gpio_read();
    xil_printf("GPIO_READ_DONE value=0x%08x\r\n", gpio_value);

    xil_printf("SNN_VERSION_BEGIN addr=0x%08x\r\n",
               HLS6D_SNN_BASEADDR + HLS6D_SNN_VERSION_OFFSET);
    version_value = hls6d_snn_version_read();
    xil_printf("SNN_VERSION_DONE value=0x%08x expected=0x%08x\r\n",
               version_value, HLS6D_SNN_VERSION_VALUE);

    xil_printf("SNN_STATUS_BEGIN addr=0x%08x\r\n",
               HLS6D_SNN_BASEADDR + HLS6D_SNN_STATUS_OFFSET);
    status_value = hls6d_snn_status_read();
    xil_printf("SNN_STATUS_DONE value=0x%08x\r\n", status_value);

    xil_printf("HLS6D_DIAG_COMPLETE gpio=0x%08x version=0x%08x status=0x%08x\r\n",
               gpio_value, version_value, status_value);
    return version_value == HLS6D_SNN_VERSION_VALUE ? 0 : 1;
}
