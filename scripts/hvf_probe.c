/* Hardware prerequisite only; not a QEMU or Windows boot test. */
#include <Hypervisor/Hypervisor.h>
#include <stdio.h>

int main(void) {
    hv_return_t result = hv_vm_create(NULL);
    printf("hv_vm_create=0x%x\n", result);
    if (result != HV_SUCCESS) return 1;
    result = hv_vm_destroy();
    printf("hv_vm_destroy=0x%x\n", result);
    return result != HV_SUCCESS;
}
