set -euo pipefail
export LC_ALL=C
root=/home/wang/p5b-rt-5.4.0
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix=$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-
test -f "$root/logs/step5.complete"
exec > >(tee "$root/logs/step5-external-modules.log") 2>&1
mkdir -p "$root/staging/vcu-modules"
tar -xf "$root/inputs/vcu-modules-source.tar" -C "$root/staging/vcu-modules"
cd "$root/src"
make ARCH=arm64 O="$root/build" M="$root/staging/vcu-modules" CROSS_COMPILE="$prefix" CC="${prefix}gcc --sysroot=$recipe/recipe-sysroot -fuse-ld=bfd" LD="${prefix}ld.bfd --sysroot=$recipe/recipe-sysroot" LOCALVERSION= -j4 modules
release=$(cat "$root/logs/kernelrelease.txt")
for name in common/allegro al5e/al5e al5d/al5d dmaproxy/dmaproxy; do
  file="$root/staging/vcu-modules/$name.ko"
  target="$root/staging/modules/lib/modules/$release/extra/$name.ko"
  test -s "$file"
  mkdir -p "$(dirname "$target")"
  "${prefix}strip" --strip-debug -o "$target" "$file"
  test "$(/sbin/modinfo -F vermagic "$target" | cut -d ' ' -f 1)" = "$release"
  /sbin/modinfo -F vermagic "$target"
done
/sbin/depmod -b "$root/staging/modules" -F "$root/build/System.map" "$release" 2>&1 | tee "$root/logs/depmod.log"
test ! -s "$root/logs/depmod.log"
git show -s --format=%ct HEAD > "$root/logs/source-date-epoch.txt"
find "$root/staging/modules/lib/modules/$release" -type f -name '*.ko' | sort > "$root/logs/modules-built.txt"
printf 'ALL_MODULES=%s\n' "$(wc -l < "$root/logs/modules-built.txt")"
touch "$root/logs/step5-external.complete"
