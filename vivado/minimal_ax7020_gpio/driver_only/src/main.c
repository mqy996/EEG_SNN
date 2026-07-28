#include "xparameters.h"
#include "xgpio.h"
#include "xil_printf.h"

#define GPIO_CHANNEL 1U
#define GPIO_BASE XPAR_AXI_GPIO_0_BASEADDR
#define GPIO_PATTERN 0x12345678U

int main(void) {
    XGpio gpio;
    int status;
    u32 value;

    xil_printf("BOOT_XGPIO\r\n");
    xil_printf("UART_OK\r\n");
    xil_printf("XGPIO_BASE=0x%08x\r\n", (unsigned)GPIO_BASE);

    xil_printf("XGPIO_INIT_BEGIN\r\n");
    status = XGpio_Initialize(&gpio, GPIO_BASE);
    xil_printf("XGPIO_INIT_STATUS=%d\r\n", status);
    if (status != XST_SUCCESS) {
        xil_printf("XGPIO_RESULT=INIT_FAIL\r\n");
        while (1) { }
    }
    xil_printf("XGPIO_INIT_DONE\r\n");

    xil_printf("XGPIO_DIR_BEGIN\r\n");
    XGpio_SetDataDirection(&gpio, GPIO_CHANNEL, 0x00000000U);
    xil_printf("XGPIO_DIR_DONE\r\n");

    xil_printf("XGPIO_WRITE_BEGIN\r\n");
    XGpio_DiscreteWrite(&gpio, GPIO_CHANNEL, GPIO_PATTERN);
    xil_printf("XGPIO_WRITE_DONE\r\n");

    xil_printf("XGPIO_READ_BEGIN\r\n");
    value = XGpio_DiscreteRead(&gpio, GPIO_CHANNEL);
    xil_printf("XGPIO_READ_VALUE=0x%08x\r\n", value);
    xil_printf("XGPIO_READ_DONE\r\n");

    xil_printf("XGPIO_RESULT=%s\r\n", value == GPIO_PATTERN ? "PASS" : "DATA_MISMATCH");
    xil_printf("DONE\r\n");
    while (1) { }
    return 0;
}
