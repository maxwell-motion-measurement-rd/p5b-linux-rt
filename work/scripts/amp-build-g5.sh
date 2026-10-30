#!/bin/bash
set -euo pipefail
r=/home/wang/p5-amp-20261030-r004
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
lp=$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-
mkdir -p "$r/build-g5"
for tool in g5_test g5_load g5_snapshot g5_recovery; do
 extra=(); if [[ $tool == g5_test || $tool == g5_recovery ]]; then extra+=("$r/protocol/amp_wire.c"); fi
 "${lp}gcc" --sysroot="$recipe/recipe-sysroot" -fuse-ld=bfd -O2 -Wall -Wextra -Werror "$r/linux-g5/$tool.c" "${extra[@]}" -o "$r/build-g5/$tool" -lrt
 "${lp}strip" "$r/build-g5/$tool"
done
sha256sum "$r"/build-g5/g5_* > "$r/build-g5/SHA256SUMS"
cat "$r/build-g5/SHA256SUMS"
