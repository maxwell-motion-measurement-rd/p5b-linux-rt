set -eu
rtwork=/home/wang/p5-rt-assess-tools-20261029
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix="$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-"
cp /tmp/rt-tests-1.0.tar.xz "$rtwork/"
tar -xf "$rtwork/rt-tests-1.0.tar.xz" -C "$rtwork"
cd "$rtwork/rt-tests-1.0"
make NUMA=0 CC="${prefix}gcc --sysroot=$recipe/recipe-sysroot" AR="${prefix}ar" CFLAGS='-O2 -Wall -Wno-nonnull' cyclictest > "$rtwork/cyclictest-1.0-build.log" 2>&1
cp "$rtwork/output/cyclictest" "$rtwork/output/cyclictest-1.10-numa-init-failed"
"${prefix}strip" --strip-debug -o "$rtwork/output/cyclictest" cyclictest
sha256sum "$rtwork/rt-tests-1.0.tar.xz" "$rtwork/output/cyclictest"
"${prefix}readelf" -d "$rtwork/output/cyclictest" | grep NEEDED
grep -n 'laptop\|duration\|affinity\|policy' src/cyclictest/cyclictest.c | head -n 10
