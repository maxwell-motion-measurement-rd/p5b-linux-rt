#!/bin/bash
set -eu
project=/home/wang/petalinux/ALIENTEK-MP
sw=$project/build/downloads/git2/github.com.Xilinx.embeddedsw.git
rev=08b9f4304d1634ed632f4276d603d834940fd55a
atf=$project/build/tmp/work/aarch64-xilinx-linux/arm-trusted-firmware/2.0-xilinx-v2020.2+gitAUTOINC+e6eea88b14-r0/git
printf '\nIDENTITY\n'
hostname
git --git-dir="$sw" rev-parse "$rev"
git -C "$atf" rev-parse HEAD
sha256sum "$project/images/linux/BOOT.BIN" "$project/project-spec/hw-description/system.xsa"
printf '\nBIF\n'
cat "$project/build/bootgen.bif"
printf '\nFSBL_HANDOFF\n'
git --git-dir="$sw" show "$rev:lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c" | nl -ba | sed -n '285,330p;550,900p'
printf '\nSTANDALONE_FILES\n'
git --git-dir="$sw" ls-tree -r --name-only "$rev" lib/bsp/standalone | grep -E 'armv8.*(boot.S|translation_table.S|xil_cache.c|xil_mmu.c)|asm_vectors.S'
printf '\nATF_SECONDARY_BOOT\n'
grep -RnE 'plat_secondary_cold_boot_setup|plat_is_my_cpu_primary|secondary.*cold|CPU3|ACPU3|RVBAR' "$atf/plat/xilinx/zynqmp" "$atf/bl31/aarch64" "$atf/lib/el3_runtime/aarch64" | head -90
printf '\nUBOOT_LAYOUT\n'
strings "$project/images/linux/u-boot.bin" | grep -E '^(bootm_size=|kernel_addr_r=|fdt_addr_r=|ramdisk_addr_r=|fdt_high=|initrd_high=)'
printf '\nXSCT_TOOLS\n'
ls -l /home/wang/tools/petalinux/2020.2/tools/xsct/bin/xsct /home/wang/tools/petalinux/2020.2/tools/xsct/gnu/aarch64/lin/aarch64-none/bin/aarch64-none-elf-gcc
printf '\nSTANDALONE_BOOT\n'
git --git-dir="$sw" show "$rev:lib/bsp/standalone/src/arm/ARMv8/64bit/gcc/boot.S" | nl -ba | sed -n '135,180p;220,245p;395,455p'
printf '\nATF_POWER\n'
sed -n '1,140p' "$atf/plat/xilinx/zynqmp/aarch64/zynqmp_helpers.S"
grep -nE 'suspend|power_domain|NODE_APU|NODE_APU_3|CPU_ON|cpu_on' "$atf/plat/xilinx/zynqmp/plat_psci.c" | head -65
printf '\nBOOT_SCRIPT\n'
strings "$project/images/linux/boot.scr"
printf '\nUBOOT_MEMORY_CONFIG\n'
grep -nE 'CONFIG_(SYS_TEXT_BASE|SYS_MALLOC_LEN|SYS_MEM_TOP_HIDE|SYS_SDRAM_BASE|SYS_BOOTM_LEN|SYS_LOAD_ADDR)' "$project/build/tmp/work/zynqmp_generic-xilinx-linux/u-boot-xlnx/v2020.01-xilinx-v2020.2+git999-r0/u-boot-xlnx-v2020.01-xilinx-v2020.2+git999/.config" || true
