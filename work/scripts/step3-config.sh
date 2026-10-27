set -euo pipefail
export LC_ALL=C
root=/home/wang/p5b-rt-5.4.0
prefix=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-
test -f "$root/logs/step2.complete"
mkdir "$root/build"
exec > >(tee "$root/logs/step3-config.log") 2>&1
cp -p "$root/inputs/original.config" "$root/build/.config"
cd "$root/src"
scripts/config --file "$root/build/.config" --enable EXPERT --disable PREEMPT_NONE --disable PREEMPT_VOLUNTARY --disable PREEMPT --enable PREEMPT_RT --disable LOCALVERSION_AUTO --set-str LOCALVERSION '-xilinx-v2020.2-p5b'
make ARCH=arm64 O="$root/build" CROSS_COMPILE="$prefix" LD="${prefix}ld.bfd" LOCALVERSION= olddefconfig
grep -qx 'CONFIG_PREEMPT_RT=y' "$root/build/.config"
grep -qx 'CONFIG_ARCH_SUPPORTS_RT=y' "$root/build/.config"
grep -qx 'CONFIG_ARM64=y' "$root/build/.config"
grep -qx 'CONFIG_ARCH_ZYNQMP=y' "$root/build/.config"
grep -qx '# CONFIG_PREEMPT_NONE is not set' "$root/build/.config"
cp -p "$root/build/.config" "$root/logs/step3-rt.config"
scripts/diffconfig "$root/inputs/original.config" "$root/build/.config" > "$root/logs/config-diff.step3.txt"
cat "$root/logs/config-diff.step3.txt"
make -s ARCH=arm64 O="$root/build" CROSS_COMPILE="$prefix" LD="${prefix}ld.bfd" LOCALVERSION= kernelrelease | tee "$root/logs/kernelrelease.txt"
printf '\nCORE_ENUMERATION_SOURCE\n'
grep -n -A115 -B8 'static void __init of_parse_and_init_cpus' arch/arm64/kernel/smp.c
printf '\nORIGINAL_FIT_SPEC\n'
cat "$root/inputs/original.its"
touch "$root/logs/step3.complete"
printf '%s\n' RT_CONFIG_OK
