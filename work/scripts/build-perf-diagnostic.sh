set -eu
original_src=/home/wang/p5b-rt-5.4.0/src
diag=/home/wang/p5-rt-diagnostics-20261029
src=$diag/perf-source
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix="$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-"
mkdir -p "$diag/perf"
git -C "$original_src" rev-parse HEAD > "$diag/source-commit.txt"
if test ! -e "$src"; then
  mkdir -p "$src"
  cp -a "$original_src/tools" "$src/"
  cp "$original_src/Makefile" "$src/"
  # This old ARM64 source includes gelf.h even when LIBELF is disabled.
  # Move only that include inside its existing feature guard, in a private copy.
  python3 - "$src/tools/perf/arch/arm64/util/sym-handling.c" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text();s=s.replace('#include <gelf.h>\n\n#ifdef HAVE_LIBELF_SUPPORT', '#ifdef HAVE_LIBELF_SUPPORT\n#include <gelf.h>');p.write_text(s)
PY
  diff -u "$original_src/tools/perf/arch/arm64/util/sym-handling.c" "$src/tools/perf/arch/arm64/util/sym-handling.c" > "$diag/perf-no-libelf.patch" || test "$?" = 1
fi
make -C "$src/tools/perf" O="$diag/perf/" ARCH=arm64 CROSS_COMPILE="$prefix" CC="${prefix}gcc --sysroot=$recipe/recipe-sysroot" LD="${prefix}ld --sysroot=$recipe/recipe-sysroot" WERROR=0 NO_LIBELF=1 NO_LIBUNWIND=1 NO_LIBDW_DWARF_UNWIND=1 NO_LIBNUMA=1 NO_LIBAUDIT=1 NO_LIBBPF=1 NO_LIBPERL=1 NO_LIBPYTHON=1 NO_SLANG=1 NO_GTK2=1 NO_DEMANGLE=1 NO_LIBCRYPTO=1 NO_LIBCAP=1 NO_ZLIB=1 NO_LZMA=1 NO_LIBZSTD=1 NO_LIBBABELTRACE=1 NO_JVMTI=1 NO_AIO=1 -j4 > "$diag/perf-build.log" 2>&1
"${prefix}strip" -o "$diag/perf-tool" "$diag/perf/perf"
gzip -c "$diag/perf-tool" > "$diag/perf.gz"
sha256sum "$diag/perf-tool" "$diag/perf.gz"
"${prefix}readelf" -d "$diag/perf-tool" | grep NEEDED
