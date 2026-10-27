set -euo pipefail
export LC_ALL=C
root=/home/wang/p5b-rt-5.4.0
recipe=/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix=$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-
test -f "$root/logs/step3.complete"
exec > >(tee "$root/logs/step4-dtb.log") 2>&1
python3 - <<'PY'
import pathlib, re
root = pathlib.Path('/home/wang/p5b-rt-5.4.0')
text = (root/'build/dtb/original.dts').read_text()
text, n = re.subn(r'\n\t\tcpu@3 \{.*?\n\t\t\};\n', '\n', text, count=1, flags=re.S)
assert n == 1
text, n = re.subn(r'^\s*cpu3 = "/cpus/cpu@3";\n', '', text, count=1, flags=re.M)
assert n == 1
text, n = re.subn(r'bootargs = "[^"]*";', 'bootargs = "earlycon console=ttyPS0,115200 rdinit=/init rw";', text, count=1)
assert n == 1
old = '\t\tinterrupts = <0x0 0x8f 0x4 0x0 0x90 0x4 0x0 0x91 0x4 0x0 0x92 0x4>;'
new = '\t\tinterrupts = <0x0 0x8f 0x4 0x0 0x90 0x4 0x0 0x91 0x4>;\n\t\tinterrupt-affinity = <0x2e 0x2f 0x30>;'
assert text.count(old) == 1
text = text.replace(old, new)
(root/'build/dtb/p5b-rt.dts').write_text(text)
PY
dtc -I dts -O dtb -o "$root/build/dtb/system.dtb" "$root/build/dtb/p5b-rt.dts" 2> "$root/logs/dtb-rt-warnings.txt"
dtc -I dtb -O dts -o "$root/build/dtb/p5b-rt.roundtrip.dts" "$root/build/dtb/system.dtb" 2> "$root/logs/dtb-rt-roundtrip-warnings.txt"
diff -u "$root/build/dtb/original.dts" "$root/build/dtb/p5b-rt.roundtrip.dts" > "$root/logs/dtb-changes.diff" || test $? -eq 1
cat "$root/logs/dtb-changes.diff"
test "$(fdtget -l "$root/build/dtb/system.dtb" /cpus | grep '^cpu@' | tr '\n' ' ')" = 'cpu@0 cpu@1 cpu@2 '
for cpu in 0 1 2; do
  test "$(fdtget -t x "$root/build/dtb/system.dtb" /cpus/cpu@$cpu reg)" = "$cpu"
  test "$(fdtget "$root/build/dtb/system.dtb" /cpus/cpu@$cpu enable-method)" = psci
done
test "$(fdtget -t x "$root/build/dtb/system.dtb" /pmu interrupt-affinity)" = '2e 2f 30'
test "$(fdtget "$root/build/dtb/system.dtb" /chosen bootargs)" = 'earlycon console=ttyPS0,115200 rdinit=/init rw'
cd "$root/src"
scripts/config --file "$root/build/.config" --set-val NR_CPUS 3
make ARCH=arm64 O="$root/build" CROSS_COMPILE="$prefix" CC="${prefix}gcc --sysroot=$recipe/recipe-sysroot -fuse-ld=bfd" LD="${prefix}ld.bfd --sysroot=$recipe/recipe-sysroot" LOCALVERSION= olddefconfig
grep -qx 'CONFIG_NR_CPUS=3' "$root/build/.config"
grep -qx 'CONFIG_PREEMPT_RT=y' "$root/build/.config"
cp -p "$root/build/.config" "$root/logs/final.config"
scripts/diffconfig "$root/inputs/original.config" "$root/build/.config" > "$root/logs/config-diff.final.txt"
sha256sum "$root/build/dtb/system.dtb"
printf 'DTB_CPUS='; fdtget -l "$root/build/dtb/system.dtb" /cpus | grep '^cpu@' | tr '\n' ' '; printf '\n'
fdtget "$root/build/dtb/system.dtb" /chosen bootargs
touch "$root/logs/step4.complete"
printf '%s\n' THREE_CORE_DTB_AND_INITRAMFS_ARGS_OK
