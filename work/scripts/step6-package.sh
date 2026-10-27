set -euo pipefail
export LC_ALL=C
root=/home/wang/p5b-rt-5.4.0
test -f "$root/logs/step5-external.complete"
exec > >(tee "$root/logs/step6-package.log") 2>&1
python3 "$root/scripts/pack-rootfs.py"
gzip -t "$root/staging/rootfs.cpio.gz"
gzip -n -9 -c "$root/build/arch/arm64/boot/Image" > "$root/build/arch/arm64/boot/Image.gz"
mkdir -p "$root/build/fit"
cat > "$root/build/fit/p5b-rt.its" <<'ITS'
/dts-v1/;
/ {
    description = "P5B Linux 5.4.0 PREEMPT_RT, A53 Core0-2, initramfs";
    #address-cells = <1>;
    images {
        kernel@1 {
            description = "P5B RT Linux kernel";
            data = /incbin/("../arch/arm64/boot/Image.gz");
            type = "kernel"; arch = "arm64"; os = "linux";
            compression = "gzip"; load = <0x80000>; entry = <0x80000>;
            hash@1 { algo = "sha256"; };
        };
        fdt@system-top.dtb {
            description = "P5B Linux Core0-2 device tree";
            data = /incbin/("../dtb/system.dtb");
            type = "flat_dt"; arch = "arm64"; compression = "none";
            hash@1 { algo = "sha256"; };
        };
        ramdisk@1 {
            description = "P5B initramfs with matching RT modules";
            data = /incbin/("../../staging/rootfs.cpio.gz");
            type = "ramdisk"; arch = "arm64"; os = "linux"; compression = "none";
            hash@1 { algo = "sha256"; };
        };
    };
    configurations {
        default = "conf@system-top.dtb";
        conf@system-top.dtb {
            description = "RT kernel, three-core FDT, initramfs";
            kernel = "kernel@1"; fdt = "fdt@system-top.dtb"; ramdisk = "ramdisk@1";
        };
    };
};
ITS
cp -p "$root/deploy/baseline/BOOT.BIN" "$root/deploy/rt/BOOT.BIN"
cp -p "$root/deploy/baseline/boot.scr" "$root/deploy/rt/boot.scr"
export SOURCE_DATE_EPOCH=$(cat "$root/logs/source-date-epoch.txt")
mkimage -f "$root/build/fit/p5b-rt.its" "$root/deploy/rt/image.ub" > "$root/logs/fit-mkimage.log" 2>&1
dumpimage -l "$root/deploy/rt/image.ub" > "$root/logs/fit-listing.txt"
python3 "$root/scripts/validate-fit.py"
cmp "$root/deploy/rt/BOOT.BIN" "$root/deploy/baseline/BOOT.BIN"
cmp "$root/deploy/rt/boot.scr" "$root/deploy/baseline/boot.scr"
touch "$root/logs/step6.complete"
printf '%s\n' RT_FIT_AND_ROOTFS_VALIDATED
