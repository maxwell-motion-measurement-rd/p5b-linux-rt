set -euo pipefail
root=/home/wang/p5b-rt-5.4.0
cache=/home/wang/petalinux/ALIENTEK-MP/build/downloads/git2/github.com.xilinx.vcu-modules.git
revision=844d4c4292e08ad8c3f22ac78e9a937395c1db4b
mkdir "$root/inputs/vcu-modules"
git --git-dir="$cache" archive "$revision" > "$root/inputs/vcu-modules-source.tar"
tar -xf "$root/inputs/vcu-modules-source.tar" -C "$root/inputs/vcu-modules"
printf '%s\n' "$revision" > "$root/logs/vcu-modules-source-revision.txt"
sha256sum "$root/inputs/vcu-modules-source.tar"
python3 "$root/scripts/cpio_newc.py" "$root/inputs/rootfs.cpio.gz" > "$root/logs/rootfs-module-autoload.txt"
cat "$root/logs/rootfs-module-autoload.txt"
printf '\nBUILD_STATUS\n'
tail -n 8 "$root/logs/kernel-build.log"
if test -f "$root/logs/step5.exitcode"; then cat "$root/logs/step5.exitcode"; fi
