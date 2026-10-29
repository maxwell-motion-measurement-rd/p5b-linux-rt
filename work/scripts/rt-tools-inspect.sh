set -eu
uname -a
date -Is
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix="$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-"
test -x "${prefix}gcc"
"${prefix}gcc" --version | head -n 1
for item in libc.so libpthread.so librt.so libnuma.so libcap.so; do
  "${prefix}gcc" --sysroot="$recipe/recipe-sysroot" -print-file-name="$item"
done
find /home/wang -maxdepth 4 -type f \( -name cyclictest -o -name '*rt-tests*.tar*' -o -name stress-ng -o -name '*stress*.tar*' \) -print 2>/dev/null | head -n 30
command -v wget
command -v make
ls -ld /mnt/hgfs/* 2>/dev/null || true
