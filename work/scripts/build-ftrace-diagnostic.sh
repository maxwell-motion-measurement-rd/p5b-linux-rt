set -euo pipefail
export LC_ALL=C
original=/home/wang/p5b-rt-5.4.0
diag=/home/wang/p5-rt-diagnostics-20261029/kernel-image
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix=$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-
mkdir -p "$diag"/{inputs,logs,scripts,staging,build/dtb,build/fit,deploy/rt,deploy/baseline}
test -e "$diag/src" || ln -s "$original/src" "$diag/src"
test -f "$diag/build/.config" || cp "$original/build/.config" "$diag/build/.config"
cp "$original/inputs/rootfs.cpio.gz" "$original/inputs/system.dtb" "$original/inputs/vcu-modules-source.tar" "$diag/inputs/"
cp "$original/build/dtb/system.dtb" "$diag/build/dtb/"
cp "$original/scripts/cpio_newc.py" "$diag/scripts/"
sed "s@/home/wang/p5b-rt-5.4.0@$diag@g" "$original/scripts/pack-rootfs.py" > "$diag/scripts/pack-rootfs.py"
cp "$original/deploy/rt/BOOT.BIN" "$original/deploy/rt/boot.scr" "$diag/deploy/baseline/"
cd "$original/src"
scripts/config --file "$diag/build/.config" --set-str LOCALVERSION '-xilinx-v2020.2-p5b-diag-ftrace' --disable LOCALVERSION_AUTO --enable FTRACE --enable FUNCTION_TRACER --enable FUNCTION_GRAPH_TRACER --enable SCHED_TRACER --enable FTRACE_SYSCALLS --enable ARM_PMU
args=(ARCH=arm64 O="$diag/build" CROSS_COMPILE="$prefix" "CC=${prefix}gcc --sysroot=$recipe/recipe-sysroot -fuse-ld=bfd" "LD=${prefix}ld.bfd --sysroot=$recipe/recipe-sysroot" LOCALVERSION=)
make "${args[@]}" olddefconfig > "$diag/logs/configure.log" 2>&1
scripts/diffconfig "$original/build/.config" "$diag/build/.config" > "$diag/logs/config-diff.txt"
grep -qx 'CONFIG_PREEMPT_RT=y' "$diag/build/.config"
grep -qx 'CONFIG_NR_CPUS=3' "$diag/build/.config"
grep -qx 'CONFIG_FTRACE=y' "$diag/build/.config"
grep -qx 'CONFIG_ARM_PMU=y' "$diag/build/.config"
make -s "${args[@]}" kernelrelease > "$diag/logs/kernelrelease.txt"
make "${args[@]}" -j4 Image modules >> "$diag/logs/kernel-build.log" 2>&1
make "${args[@]}" INSTALL_MOD_PATH="$diag/staging/modules" INSTALL_MOD_STRIP=1 DEPMOD=/sbin/depmod modules_install > "$diag/logs/modules-install.log" 2>&1
mkdir -p "$diag/staging/vcu-modules"
tar -xf "$diag/inputs/vcu-modules-source.tar" -C "$diag/staging/vcu-modules"
make "${args[@]}" M="$diag/staging/vcu-modules" -j2 modules > "$diag/logs/external-build.log" 2>&1
release=$(cat "$diag/logs/kernelrelease.txt")
for name in common/allegro al5e/al5e al5d/al5d dmaproxy/dmaproxy; do
  target="$diag/staging/modules/lib/modules/$release/extra/$name.ko"
  mkdir -p "$(dirname "$target")"
  "${prefix}strip" --strip-debug -o "$target" "$diag/staging/vcu-modules/$name.ko"
done
/sbin/depmod -b "$diag/staging/modules" -F "$diag/build/System.map" "$release" > "$diag/logs/depmod.log" 2>&1
git show -s --format=%ct HEAD > "$diag/logs/source-date-epoch.txt"
python3 "$diag/scripts/pack-rootfs.py" > "$diag/logs/package.log" 2>&1
gzip -n -9 -c "$diag/build/arch/arm64/boot/Image" > "$diag/build/arch/arm64/boot/Image.gz"
sed 's/P5B Linux 5.4.0 PREEMPT_RT, A53 Core0-2, initramfs/P5 RT DIAGNOSTIC ftrace and PMU, not original baseline/' "$original/build/fit/p5b-rt.its" > "$diag/build/fit/p5b-rt.its"
SOURCE_DATE_EPOCH=$(cat "$diag/logs/source-date-epoch.txt") mkimage -f "$diag/build/fit/p5b-rt.its" "$diag/deploy/rt/image.ub" > "$diag/logs/fit-build.log" 2>&1
cp "$diag/deploy/baseline/BOOT.BIN" "$diag/deploy/baseline/boot.scr" "$diag/deploy/rt/"
dumpimage -l "$diag/deploy/rt/image.ub" > "$diag/logs/fit-listing.txt"
sha256sum "$diag/deploy/rt/image.ub" > "$diag/logs/image.sha256"
cmp "$diag/build/dtb/system.dtb" "$original/build/dtb/system.dtb"
touch "$diag/logs/BUILD_COMPLETE"
cat "$diag/logs/kernelrelease.txt" "$diag/logs/image.sha256"
