set -eu
rtwork=/home/wang/p5-rt-assess-tools-20261029
mkdir -p "$rtwork"
cd "$rtwork"
wget -q --timeout=25 -O rt-tests-1.10.tar.xz https://cdn.kernel.org/pub/linux/utils/rt-tests/rt-tests-1.10.tar.xz
sha256sum rt-tests-1.10.tar.xz
tar -xf rt-tests-1.10.tar.xz
grep -nE 'NUMA|CAP|cyclictest|LIBS|CFLAGS' rt-tests-1.10/Makefile | head -n 50
grep -nE 'numa|capability' rt-tests-1.10/src/cyclictest/cyclictest.c | head -n 20
