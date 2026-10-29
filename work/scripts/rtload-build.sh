set -eu
rtwork=/home/wang/p5-rt-assess-tools-20261029
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix="$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-"
"${prefix}gcc" --sysroot="$recipe/recipe-sysroot" -O2 -Wall -Wextra "$rtwork/rtload.c" -o "$rtwork/output/rtload"
"${prefix}strip" --strip-debug "$rtwork/output/rtload"
file "$rtwork/output/rtload"
sha256sum "$rtwork/output/rtload"
