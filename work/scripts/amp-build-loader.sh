#!/bin/bash
set -euo pipefail
root=/home/wang/p5-amp-20261030-r001
baseline=/home/wang/p5b-rt-5.4.0
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix=$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-
# Independent build copy: no hard links, and no writes to the baseline build.
if test ! -e "$root/kernel-build"; then
    cp -a "$baseline/build" "$root/kernel-build"
fi
make -C "$baseline/src" ARCH=arm64 O="$root/kernel-build" M="$root/linux" \
    CROSS_COMPILE="$prefix" CC="${prefix}gcc --sysroot=$recipe/recipe-sysroot -fuse-ld=bfd" \
    LD="${prefix}ld.bfd --sysroot=$recipe/recipe-sysroot" LOCALVERSION= -j4 modules
/sbin/modinfo "$root/linux/p5_core3_boot.ko"
cat "$root/inputs/p5b-rt.dts" "$root/inputs/p5b-amp-memory.dtsi" > "$root/build/amp-candidate.dts"
dtc -I dts -O dtb -o "$root/build/amp-candidate.dtb" "$root/build/amp-candidate.dts" 2>"$root/build/dtc-warnings.txt"
fdtget -t x "$root/build/amp-candidate.dtb" /core3-heartbeat memory-region
elfprefix=/home/wang/tools/petalinux/2020.2/tools/xsct/gnu/aarch64/lin/aarch64-none/bin/aarch64-none-elf-
"${elfprefix}objcopy" -O binary "$root/build/core3-heartbeat.elf" "$root/build/p5-core3-heartbeat.bin"
sha256sum "$root/build/p5-core3-heartbeat.bin" "$root/linux/p5_core3_boot.ko" "$root/build/amp-candidate.dtb"
printf '\nLOADER_OFFLINE_BUILD_COMPLETE_NO_BOARD_ACTION\n'
