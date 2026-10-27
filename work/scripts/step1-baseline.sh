set -euo pipefail
export LC_ALL=C
project=/home/wang/petalinux/ALIENTEK-MP
source=$project/components/yocto/workspace/sources/linux-xlnx
root=/home/wang/p5b-rt-5.4.0
recipe=$project/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0
prefix=$recipe/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-
test "$(git -C "$source" rev-parse HEAD)" = 62ea514294a0c9a80455e51f1f4de36e66e8c546
test ! -e "$root"
mkdir -p "$root"/{inputs,logs,staging,deploy/baseline,deploy/rt,scripts}
exec > >(tee "$root/logs/step1-baseline.log") 2>&1
date -Is
git -C "$source" rev-parse HEAD
git -C "$source" --no-optional-locks status --porcelain=v1 --untracked-files=all > "$root/logs/original-source-status.txt"
git -C "$source" diff --quiet
git -C "$source" diff --cached --quiet
git -C "$source" symbolic-ref --short HEAD
git -C "$source" describe --tags --always
for name in BOOT.BIN boot.scr image.ub; do
  cp -p "$project/images/linux/$name" "$root/deploy/baseline/$name"
  cmp "$project/images/linux/$name" "$root/deploy/baseline/$name"
done
(cd "$root/deploy/baseline"; sha256sum BOOT.BIN boot.scr image.ub > SHA256SUMS; sha256sum -c SHA256SUMS)
printf '%s\n' 'Original project boot files, preserved byte for byte; hardware boot has not been verified in this run.' > "$root/deploy/baseline/STATUS.txt"
cp -p "$recipe/linux-xlnx-5.4+git999/.config" "$root/inputs/original.config"
for name in system.dtb rootfs.cpio.gz rootfs.tar.gz; do
  cp -p "$project/images/linux/$name" "$root/inputs/$name"
  cmp "$project/images/linux/$name" "$root/inputs/$name"
done
cp -p "$project/project-spec/configs/config" "$root/inputs/petalinux-project.config"
cp -p "$project/project-spec/hw-description/system.xsa" "$root/inputs/system.xsa"
cp -a "$project/components/plnx_workspace/device-tree/device-tree" "$root/inputs/device-tree"
cp -a "$project/project-spec/meta-user/recipes-bsp/device-tree/files" "$root/inputs/device-tree-user"
find "$project/build/tmp/deploy/images/zynqmp-generic" -maxdepth 1 -name 'fitImage-its-petalinux-image-minimal-*.its' -type f -print | sort > "$root/logs/original-fit-sources.txt"
its=$(tail -n 1 "$root/logs/original-fit-sources.txt")
test -n "$its"
cp -p "$its" "$root/inputs/original.its"
for tool in gcc as ld.bfd ar nm objcopy strip; do
  "${prefix}${tool}" --version | head -n 1
done
for tool in make gcc bc bison flex cpio gzip mkimage dumpimage dtc fdtget python3 fakeroot; do command -v "$tool"; done
/sbin/depmod --version
df -h /home/wang
free -h
nproc
dumpimage -l "$root/deploy/baseline/image.ub" > "$root/logs/original-fit.txt"
fdtget "$root/inputs/system.dtb" /chosen bootargs
(cd "$root/inputs"; find . -type f -print0 | sort -z | xargs -0 sha256sum > "$root/logs/inputs-sha256.initial.txt")
printf '%s\n' "PROJECT=$project" "SOURCE=$source" "ROOT=$root" "RECIPE=$recipe" "CROSS_COMPILE=$prefix" > "$root/logs/build-paths.txt"
printf '%s\n' BASELINE_SNAPSHOT_OK
