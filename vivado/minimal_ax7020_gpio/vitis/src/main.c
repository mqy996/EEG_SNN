#include "xil_io.h"
#include "xil_printf.h"

#define AXI_GPIO_BASEADDR 0x41200000U
#define AXI_GPIO_DATA      0x00U
#define AXI_GPIO_TRI       0x04U

static unsigned read32(unsigned offset) {
    return Xil_In32(AXI_GPIO_BASEADDR + offset);
}

static int check_data(unsigned index, unsigned expected) {
    unsigned actual = read32(AXI_GPIO_DATA);
    xil_printf("GPIO_DATA_READ%u=0x%08x EXPECTED=0x%08x\r\n", index, actual, expected);
    return actual == expected ? 0 : 1;
}

int main(void) {
    unsigned failures = 0U;
    xil_printf("BOOT\r\n");
    xil_printf("UART_OK\r\n");
    xil_printf("GPIO_BASE=0x%08x\r\n", AXI_GPIO_BASEADDR);
    xil_printf("GPIO_TRI_READ_BEGIN\r\n");
    xil_printf("GPIO_TRI_READ=0x%08x\r\n", read32(AXI_GPIO_TRI));
    xil_printf("GPIO_DATA_READ_BEGIN\r\n");
    xil_printf("GPIO_DATA_INITIAL=0x%08x\r\n", read32(AXI_GPIO_DATA));

    xil_printf("GPIO_WRITE_1_BEGIN\r\n");
    Xil_Out32(AXI_GPIO_BASEADDR + AXI_GPIO_DATA, 0x12345678U);
    failures |= (unsigned)check_data(1U, 0x12345678U);
    xil_printf("GPIO_WRITE_2_BEGIN\r\n");
    Xil_Out32(AXI_GPIO_BASEADDR + AXI_GPIO_DATA, 0xA5A55A5AU);
    failures |= (unsigned)check_data(2U, 0xA5A55A5AU);

    xil_printf("GPIO_REPEAT_BEGIN\r\n");
    for (unsigned i = 0U; i < 16U; ++i) {
        unsigned value = 0x10000000U + i;
        Xil_Out32(AXI_GPIO_BASEADDR + AXI_GPIO_DATA, value);
        failures |= (unsigned)check_data(i + 3U, value);
    }
    xil_printf("GPIO_REPEAT_%s\r\n", failures == 0U ? "OK" : "FAIL");
    xil_printf("RESULT=%s\r\n", failures == 0U ? "PASS" : "FAIL");
    xil_printf("DONE\r\n");
    while (1) { }
    return failures == 0U ? 0 : 1;
}
