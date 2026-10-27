set -euo pipefail
export LC_ALL=C
root=/home/wang/p5b-rt-5.4.0
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix=$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-
export PATH="$(dirname "$prefix"):/usr/sbin:/sbin:$PATH"
trap 'rc=$?; printf "%s\n" "$rc" > "$root/logs/step5.exitcode"; exit "$rc"' EXIT
test -f "$root/logs/step4.complete"
date -Is > "$root/logs/step5-started.txt"
cd "$root/src"
args=(ARCH=arm64 O="$root/build" CROSS_COMPILE="$prefix" "CC=${prefix}gcc --sysroot=$recipe/recipe-sysroot -fuse-ld=bfd" "LD=${prefix}ld.bfd --sysroot=$recipe/recipe-sysroot" LOCALVERSION=)
printf 'make '; printf '%q ' "${args[@]}" -j4 Image modules; printf '\n'
make "${args[@]}" -j4 Image modules > "$root/logs/kernel-build.log" 2>&1
release=$(make -s "${args[@]}" kernelrelease)
printf '%s\n' "$release" > "$root/logs/kernelrelease.txt"
test "$release" = 5.4.0-rt1-xilinx-v2020.2-p5b
make "${args[@]}" INSTALL_MOD_PATH="$root/staging/modules" INSTALL_MOD_STRIP=1 DEPMOD=/sbin/depmod modules_install > "$root/logs/modules-install.log" 2>&1
"${prefix}readelf" -h "$root/build/vmlinux" > "$root/logs/vmlinux-elf-header.txt"
grep -q 'AArch64' "$root/logs/vmlinux-elf-header.txt"
test -s "$root/build/arch/arm64/boot/Image"
test -s "$root/build/System.map"
test -s "$root/build/Module.symvers"
test -f "$root/staging/modules/lib/modules/$release/modules.dep"
grep -qx 'CONFIG_PREEMPT_RT=y' "$root/build/.config"
grep -qx 'CONFIG_NR_CPUS=3' "$root/build/.config"
cp -p "$root/build/.config" "$root/logs/final.config"
sha256sum "$root/build/arch/arm64/boot/Image" "$root/build/vmlinux" "$root/build/System.map" "$root/build/Module.symvers" > "$root/logs/kernel-artifacts.sha256"
find "$root/staging/modules/lib/modules/$release" -type f -name '*.ko' | sort > "$root/logs/modules-built.txt"
date -Is > "$root/logs/step5-finished.txt"
touch "$root/logs/step5.complete"
printf 'KERNEL_BUILD_OK release=%s modules=%s\n' "$release" "$(wc -l < "$root/logs/modules-built.txt")"
