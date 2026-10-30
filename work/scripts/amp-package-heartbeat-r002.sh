#!/bin/bash
set -euo pipefail
r=/home/wang/p5-amp-20261030-r002
b=/home/wang/p5b-rt-5.4.0
mkdir -p "$r/package/experiment" "$r/package/rollback"
# Restricted first heartbeat configuration, distinct from performance baseline.
python3 - "$r" <<'PY'
import pathlib,sys
r=pathlib.Path(sys.argv[1])
text=(r/'inputs/p5b-rt.dts').read_text()+(r/'inputs/p5b-amp-memory.dtsi').read_text()
text=text.replace('earlycon console=ttyPS0,115200 rdinit=/init rw','earlycon console=ttyPS0,115200 rdinit=/init rw cpuidle.off=1 clk_ignore_unused pd_ignore_unused')
(r/'build/amp-candidate.dts').write_text(text)
PY
dtc -I dts -O dtb -o "$r/build/amp-candidate.dtb" "$r/build/amp-candidate.dts" 2>"$r/build/dtc-warnings.txt"
python3 "$r/scripts/amp-package-heartbeat.py"
cat > "$r/build/heartbeat.its" <<'EOF'
/dts-v1/;
/ {
 description = "P5 AMP heartbeat r002 manual PMU start, NOT validated on board";
 #address-cells = <1>;
 images {
  kernel { data = /incbin/("/home/wang/p5b-rt-5.4.0/build/arch/arm64/boot/Image.gz"); type = "kernel"; arch = "arm64"; os = "linux"; compression = "gzip"; load = <0x80000>; entry = <0x80000>; hash { algo = "sha256"; }; };
  fdt { data = /incbin/("amp-candidate.dtb"); type = "flat_dt"; arch = "arm64"; compression = "none"; hash { algo = "sha256"; }; };
  ramdisk { data = /incbin/("amp-rootfs.cpio.gz"); type = "ramdisk"; arch = "arm64"; os = "linux"; compression = "none"; hash { algo = "sha256"; }; };
 };
 configurations { default = "amp"; amp { kernel = "kernel"; fdt = "fdt"; ramdisk = "ramdisk"; }; };
};
EOF
mkimage -f "$r/build/heartbeat.its" "$r/package/experiment/image.ub"
for f in BOOT.BIN boot.scr; do cp -p "$b/deploy/rt/$f" "$r/package/experiment/$f"; done
for f in BOOT.BIN boot.scr image.ub; do cp -p "$b/deploy/rt/$f" "$r/package/rollback/$f"; done
for d in experiment rollback; do (cd "$r/package/$d" && sha256sum BOOT.BIN boot.scr image.ub > SHA256SUMS && sha256sum -c SHA256SUMS); done
printf '\nBOOTARGS\n'
fdtget "$r/build/amp-candidate.dtb" /chosen bootargs
printf '\nPACKAGE_CREATED_NOT_DEPLOYED\n'
