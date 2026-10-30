/* Offline candidate only. Requires cold-reset A53-3 at EL3, MMU/I/D off.
 * No BSP, UART, GIC, SMC, shared cache maintenance or peripheral writes.
 */
.section .text.boot,"ax"
.global _start
_start:
    msr daifset, #15
    mrs x0, CurrentEL
    cmp x0, #12
    b.ne park
    mrs x0, mpidr_el1
    ubfx x1, x0, #0, #24
    cmp x1, #3
    b.ne park
    mrs x1, sctlr_el3
    ldr x2, =0x1005
    tst x1, x2
    b.ne park
    msr spsel, #1
    ldr x1, =__stack_top
    mov sp, x1
    ldr x1, =vectors
    msr vbar_el3, x1
    /* No lower-EL execution; permit EL3 access to NS-mapped DDR. */
    mov x1, #0x30
    msr scr_el3, x1
    isb
    ldr x1, =__bss_start
    ldr x2, =__bss_end
1:  cmp x1, x2
    b.hs 2f
    str xzr, [x1], #8
    b 1b
2:  /* L1[1] -> L2; two identity-mapped 2MiB Normal-NC NS blocks. */
    ldr x1, =l1_table
    ldr x2, =l2_table
    orr x3, x2, #3
    str x3, [x1, #8]
    ldr x3, =0x60000721 /* block, AF, inner-shareable, NS, AttrIdx=0 */
    str x3, [x2, #2048]
    ldr x3, =0x0040000060200721 /* shared block XN */
    str x3, [x2, #2056]
    dsb sy
    msr ttbr0_el3, x1
    mov x1, #0x44 /* MAIR Attr0 Normal, Inner/Outer Non-cacheable */
    msr mair_el3, x1
    ldr x1, =0x80803020 /* RES1, PS=32bit, 4KiB, SH=inner, NC walks, VA=32bit */
    msr tcr_el3, x1
    isb
    tlbi alle3
    dsb sy
    isb
    mrs x1, sctlr_el3
    orr x1, x1, #1 /* enable MMU, leave I/D cache off */
    msr sctlr_el3, x1
    isb
    ldr x20, =0x60200000
    str wzr, [x20] /* invalidate publication until status is complete */
    mov w1, #2
    str w1, [x20, #4] /* version */
    mov w1, #3
    str w1, [x20, #8] /* core */
    mov w1, #12
    str w1, [x20, #12] /* CurrentEL encoding */
    mrs x24, cntfrq_el0
    str x24, [x20, #88] /* reset value is not a reliable frequency */
    ldr x21, [x20, #48] /* initialized Linux frequency, supplied before wake */
    str x21, [x20, #16]
    mrs x22, cntpct_el0
    str x22, [x20, #24] /* boot token, not a persistent boot counter */
    mov x23, #0
    str x23, [x20, #32] /* heartbeat */
    str wzr, [x20, #44] /* reason: 0=none, 1=bad hint, 2=exception, 3=readback */
    ldr w1, [x20, #56]
    ldr w2, =0x46525132
    cmp w1, w2
    b.ne bad_frequency
    lsr x1, x21, #32
    cbnz x1, bad_frequency
    cmp x21, #10
    b.lo bad_frequency
    /* CNTFRQ is per-PE software metadata; this does not retune the counter. */
    msr cntfrq_el0, x21
    isb
    mrs x1, cntfrq_el0
    str x1, [x20, #96]
    cmp x1, x21
    b.ne frequency_readback_failed
    mov w1, #1
    str w1, [x20, #40] /* RUNNING */
    dsb sy
    ldr w1, =0x504d4143
    str w1, [x20] /* publish magic last */
    dsb sy
    mov x1, #10
    udiv x21, x21, x1
3:  isb
    mrs x1, cntpct_el0
    sub x2, x1, x22
    cmp x2, x21
    b.lo 3b
    mov x22, x1
    add x23, x23, #1
    str x23, [x20, #32]
    dsb sy
    b 3b
bad_frequency:
    mov w1, #1
    b software_fault
frequency_readback_failed:
    mov w1, #3
software_fault:
    str w1, [x20, #44]
    str xzr, [x20, #64]
    str xzr, [x20, #72]
    str xzr, [x20, #80]
    mov w1, #2
    str w1, [x20, #40]
    dsb sy
    ldr w1, =0x504d4143
    str w1, [x20]
    dsb sy
    b park
fault:
    ldr x20, =0x60200000
    mov w1, #2
    str w1, [x20, #44]
    mrs x1, esr_el3
    str x1, [x20, #64]
    mrs x1, elr_el3
    str x1, [x20, #72]
    mrs x1, far_el3
    str x1, [x20, #80]
    mov w1, #2
    str w1, [x20, #40]
    dsb sy
park:
    wfe
    b park
.balign 2048
vectors:
.rept 16
    b fault
    .space 124
.endr
.section .bss,"aw",%nobits
.balign 4096
l1_table: .skip 4096
l2_table: .skip 4096
.section .note.GNU-stack,"",%progbits
