#!/bin/bash
set -euo pipefail
r=/home/wang/p5-amp-20261030-r003
b=/home/wang/p5b-rt-5.4.0
p=/home/wang/tools/petalinux/2020.2/tools/xsct/gnu/aarch64/lin/aarch64-none/bin/aarch64-none-elf-
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
lp=$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-
mkdir -p "$r/build"
for source in "$r/core3/start-comm.S" "$r/core3/ipc.c" "$r/protocol/amp_wire.c"; do
 name=$(basename "$source"); name=${name%.*}
 "${p}gcc" -c -mcpu=cortex-a53 -O2 -mgeneral-regs-only -ffreestanding -fno-builtin -fno-stack-protector -fno-pic -fno-pie -Wall -Wextra -Werror "$source" -o "$r/build/$name.o"
done
"${p}ld" -T "$r/core3/link.ld" -Map="$r/build/core3-comm.map" -o "$r/build/core3-comm.elf" "$r/build/start-comm.o" "$r/build/ipc.o" "$r/build/amp_wire.o"
"${p}objcopy" -O binary "$r/build/core3-comm.elf" "$r/build/p5-core3-comm.bin"
"${p}readelf" -h -l -S "$r/build/core3-comm.elf" > "$r/build/readelf.txt"
"${p}objdump" -d "$r/build/core3-comm.elf" > "$r/build/disassembly.txt"
"${p}nm" -n "$r/build/core3-comm.elf" > "$r/build/symbols.txt"
make -C "$b/src" ARCH=arm64 O=/home/wang/p5-amp-20261030-r001/kernel-build M="$r/linux-comm" CROSS_COMPILE="$lp" \
 CC="${lp}gcc --sysroot=$recipe/recipe-sysroot -fuse-ld=bfd" LD="${lp}ld.bfd --sysroot=$recipe/recipe-sysroot" LOCALVERSION= -j4 modules
"${lp}strip" --strip-debug -o "$r/build/p5_core3_comm.ko" "$r/linux-comm/p5_core3_comm.ko"
"${lp}gcc" --sysroot="$recipe/recipe-sysroot" -fuse-ld=bfd -O2 -Wall -Wextra -Werror "$r/linux-comm/g3_test.c" "$r/protocol/amp_wire.c" -o "$r/build/g3_test" -lrt
"${lp}strip" "$r/build/g3_test"
/sbin/modinfo "$r/build/p5_core3_comm.ko"
stat -c '%n %s' "$r/build/p5-core3-comm.bin" "$r/build/p5_core3_comm.ko" "$r/build/g3_test"
sha256sum "$r/build/p5-core3-comm.bin" "$r/build/p5_core3_comm.ko" "$r/build/g3_test" > "$r/build/SHA256SUMS"
cat "$r/build/SHA256SUMS"
