set -euo pipefail
export LC_ALL=C
root=/home/wang/p5b-rt-5.4.0
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix=$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-
sysroot=$recipe/recipe-sysroot
exec > >(tee "$root/logs/step3-toolchain-refine.log") 2>&1
printf 'int main(void) { return 0; }\n' | "${prefix}gcc" --sysroot="$sysroot" -fuse-ld=bfd -x c -o "$root/staging/toolchain-link-check.elf" -
"${prefix}readelf" -h "$root/staging/toolchain-link-check.elf" | grep -E 'Class:|Machine:'
cd "$root/src"
make ARCH=arm64 O="$root/build" CROSS_COMPILE="$prefix" CC="${prefix}gcc --sysroot=$sysroot -fuse-ld=bfd" LD="${prefix}ld.bfd --sysroot=$sysroot" LOCALVERSION= olddefconfig
scripts/diffconfig "$root/inputs/original.config" "$root/build/.config" > "$root/logs/config-diff.step3.final.txt"
cat "$root/logs/config-diff.step3.final.txt"
grep -E '^CONFIG_(PREEMPT_RT|ARM64|ARCH_ZYNQMP|SMP|NR_CPUS|BLK_DEV_INITRD|RD_GZIP|SERIAL_XILINX_PS_UART|MMC_SDHCI_OF_ARASAN|XILINX_FIRMWARE|CC_CAN_LINK)=' "$root/build/.config"
cp -p "$root/build/.config" "$root/logs/step3-rt.final.config"
printf '%s\n' RT_CONFIG_TOOLCHAIN_REVIEW_OK
