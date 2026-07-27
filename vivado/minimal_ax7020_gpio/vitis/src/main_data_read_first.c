#include "xil_io.h"
#include "xil_printf.h"
#define AXI_GPIO_BASEADDR 0x41200000U
#define AXI_GPIO_DATA 0x00U
#define AXI_GPIO_TRI 0x04U
int main(void) {
    unsigned actual;
    xil_printf("BOOT_DATA_READ_FIRST\r\n");
    xil_printf("UART_OK\r\n");
    xil_printf("GPIO_BASE=0x%08x\r\n", AXI_GPIO_BASEADDR);
    xil_printf("GPIO_DATA_READ_BEGIN\r\n");
    actual = Xil_In32(AXI_GPIO_BASEADDR + AXI_GPIO_DATA);
    xil_printf("GPIO_DATA_INITIAL=0x%08x\r\n", actual);
    xil_printf("GPIO_TRI_READ_BEGIN\r\n");
    actual = Xil_In32(AXI_GPIO_BASEADDR + AXI_GPIO_TRI);
    xil_printf("GPIO_TRI_READ=0x%08x\r\n", actual);
    xil_printf("DONE\r\n");
    while (1) { }
    return 0;
}
