set -eu
rtwork=/home/wang/p5-rt-assess-tools-20261029
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix="$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-"
export PATH="$(dirname "$prefix"):$PATH"
export CC="${prefix}gcc --sysroot=$recipe/recipe-sysroot"
export AR="${prefix}ar"
export RANLIB="${prefix}ranlib"
cd "$rtwork"
wget -q --timeout=30 -O numactl-2.0.12.tar.gz https://deb.debian.org/debian/pool/main/n/numactl/numactl_2.0.12.orig.tar.gz
sha256sum numactl-2.0.12.tar.gz
tar -xf numactl-2.0.12.tar.gz
cd numactl-2.0.12
./configure --host=aarch64-xilinx-linux --prefix="$rtwork/numa-install" --disable-shared --enable-static > "$rtwork/numa-configure.log" 2>&1
make -j4 > "$rtwork/numa-build.log" 2>&1
make install > "$rtwork/numa-install.log" 2>&1
cd "$rtwork/rt-tests-1.10"
make -j4 CC="$CC" AR="$AR" CFLAGS='-O2 -Wall -Wno-nonnull' CPPFLAGS="-D_GNU_SOURCE -Isrc/include -I$rtwork/numa-install/include" RTTESTNUMA="-lrttestnuma $rtwork/numa-install/lib/libnuma.a" cyclictest > "$rtwork/cyclictest-build.log" 2>&1
mkdir -p "$rtwork/output"
"${prefix}strip" --strip-debug -o "$rtwork/output/cyclictest" cyclictest
file "$rtwork/output/cyclictest"
"${prefix}readelf" -d "$rtwork/output/cyclictest" | grep NEEDED
"${prefix}readelf" -l "$rtwork/output/cyclictest" | grep interpreter
sha256sum "$rtwork/output/cyclictest"
