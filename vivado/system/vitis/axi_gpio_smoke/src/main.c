#include "xil_io.h"
#include "xil_printf.h"

#define AXI_GPIO_BASEADDR 0x41200000U
#define AXI_GPIO_DATA      0x00U
#define AXI_GPIO_TRI       0x04U

static int check_pattern(unsigned index, unsigned value, unsigned expected) {
    unsigned actual = Xil_In32(AXI_GPIO_BASEADDR + AXI_GPIO_DATA);
    xil_printf("AXI_GPIO_READ%u=0x%08x EXPECTED=0x%08x\r\n", index, actual, expected);
    return actual == expected ? 0 : 1;
}

int main(void) {
    unsigned failures = 0U;
    xil_printf("AXI_GPIO_TEST_20260727_V1\r\n");
    xil_printf("AXI_GPIO_BASE=0x%08x\r\n", AXI_GPIO_BASEADDR);

    xil_printf("AXI_GPIO_TRI=0x%08x\r\n",
               Xil_In32(AXI_GPIO_BASEADDR + AXI_GPIO_TRI));

    Xil_Out32(AXI_GPIO_BASEADDR + AXI_GPIO_DATA, 0x12345678U);
    failures |= (unsigned)check_pattern(1U, 0x12345678U, 0x12345678U);
    Xil_Out32(AXI_GPIO_BASEADDR + AXI_GPIO_DATA, 0xA5A55A5AU);
    failures |= (unsigned)check_pattern(2U, 0xA5A55A5AU, 0xA5A55A5AU);

    xil_printf("AXI_GPIO_TEST_%s\r\n", failures == 0U ? "PASS" : "FAIL");
    while (1) {
    }
    return failures == 0U ? 0 : 1;
}
