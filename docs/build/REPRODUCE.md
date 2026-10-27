# 源码重建说明

## 复现范围与输入

若只复现已记录的上板结果，按根 README 下载 Release 启动包、先启动 baseline 再启动 RT 即可。以下说明用于从源码重建，沿用本轮原 BSP 输入，不把构建成功等同于实时性能或完整板级适配通过。

固定版本：

| 输入 | 固定值 |
| --- | --- |
| PetaLinux／Vivado 工程 | 2020.2，原 ALIENTEK-MP 工程，XSA 为 xczu4ev-sfvc784-2-i |
| 厂商源码 | Xilinx Linux 5.4.0，62ea514294a0c9a80455e51f1f4de36e66e8c546 |
| RT 移植提交 | e4cc2d02d270570055fe2b46ca2eb17c21938504 |
| 原 RT 输入 | meta-retis 02995952c2df1819657f2998e6e3a63c0e2aaa63 的 patch-5.4.3-rt1.patch |
| 配置／设备树／FIT | configs/p5b-rt.config、configs/p5b-rt.dts、configs/p5b-rt.its |
| 交叉工具链 | aarch64-xilinx-linux-gcc 9.2.0，binutils 2.32.0.20190204，配套 recipe sysroot |
| 外部模块 | Xilinx/vcu-modules，844d4c4292e08ad8c3f22ac78e9a937395c1db4b |
| 原根文件系统 | 原工程 rootfs.cpio.gz；保留用户空间和 Unix 元数据，只更新模块与匹配 DTB |

构建主机为 Ubuntu 18.04，4 个 vCPU、约 7.8 GiB 内存，本轮使用 -j4。需要 make、主机 gcc、bc、bison、flex、cpio、gzip、dtc／fdtget、mkimage／dumpimage、Python 3、kmod（depmod／modinfo）和对应开发依赖。依赖以原工程已有且实际使用的工具为准；此说明未在另一台全新主机重新执行。

仓库不含完整原 BSP、XSA、工具链和原始 rootfs 的源码重建输入。应取得与本轮相同的 ALIENTEK-MP 工程与构建缓存，或准备等价输入；只克隆本仓库不足以从零生成相同 BOOT.BIN。Release 已包含本轮两套可部署文件。

以下命令是整理后的重建方法，使用独立新目录，不在已完成目录重新初始化。原执行脚本保存于 work/scripts，其硬编码路径和完成标记反映本轮环境，不是任意机器上可直接循环运行的安装器。

## 设置路径与校验输入

在 Ubuntu Bash 中，将 REPO 改为本仓库克隆位置；PROJECT 为原 PetaLinux 工程。ROOT 必须是不存在的新目录。路径变量不使用系统保留变量。

```bash
set -euo pipefail
export LC_ALL=C
REPO=/path/to/p5b-linux-rt
PROJECT=/home/wang/petalinux/ALIENTEK-MP
KERNEL_REPO="$PROJECT/components/yocto/workspace/sources/linux-xlnx"
RECIPE="$PROJECT/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0"
PREFIX="$RECIPE/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-"
SYSROOT="$RECIPE/recipe-sysroot"
ROOT=/home/wang/p5b-rt-rebuild
export ROOT
export PATH="$(dirname "$PREFIX"):/usr/sbin:/sbin:$PATH"
test ! -e "$ROOT"
test -x "${PREFIX}gcc"
git -C "$KERNEL_REPO" cat-file -e 62ea514294a0c9a80455e51f1f4de36e66e8c546^{commit}
printf '%s  %s\n' \
  684ad81ec7d25bd4b268ae5ced3c24bc53b3595aea5c528518cdeeb2e8bee26a \
  "$REPO/work/inputs/patch-5.4.3-rt1.patch" | sha256sum -c -
mkdir -p "$ROOT"/{inputs,logs,staging,deploy/baseline,deploy/rt,scripts,build/dtb,build/fit}
```

不要仅按目录名选择另一版 Linux。完整恢复 RT 提交的方法见 kernel-git-backup.md；或在固定父提交应用仓库的 format-patch，如下所示。二者与原 RT 补丁是替代方式，不能叠加。

```bash
git -C "$KERNEL_REPO" worktree add --detach "$ROOT/src" \
  62ea514294a0c9a80455e51f1f4de36e66e8c546
git -C "$ROOT/src" apply --check "$REPO/patches/0001-apply-preempt-rt-to-xilinx-5.4.0.patch"
git -C "$ROOT/src" am "$REPO/patches/0001-apply-preempt-rt-to-xilinx-5.4.0.patch"
cp "$REPO/configs/p5b-rt.config" "$ROOT/build/.config"
args=(ARCH=arm64 O="$ROOT/build" CROSS_COMPILE="$PREFIX"
      "CC=${PREFIX}gcc --sysroot=$SYSROOT -fuse-ld=bfd"
      "LD=${PREFIX}ld.bfd --sysroot=$SYSROOT" LOCALVERSION=)
make -C "$ROOT/src" "${args[@]}" olddefconfig
release=$(make -s -C "$ROOT/src" "${args[@]}" kernelrelease)
test "$release" = 5.4.0-rt1-xilinx-v2020.2-p5b
grep -x 'CONFIG_PREEMPT_RT=y' "$ROOT/build/.config"
grep -x 'CONFIG_NR_CPUS=3' "$ROOT/build/.config"
```

## 编译内核与三核 DTB

```bash
make -C "$ROOT/src" "${args[@]}" -j4 Image modules > "$ROOT/logs/kernel-build.log" 2>&1
make -C "$ROOT/src" "${args[@]}" INSTALL_MOD_PATH="$ROOT/staging/modules" \
  INSTALL_MOD_STRIP=1 DEPMOD=/sbin/depmod modules_install > "$ROOT/logs/modules-install.log" 2>&1
dtc -I dts -O dtb -o "$ROOT/build/dtb/system.dtb" "$REPO/configs/p5b-rt.dts" \
  2> "$ROOT/logs/dtb-warnings.txt"
fdtget -l "$ROOT/build/dtb/system.dtb" /cpus
for cpu in 0 1 2; do
  test "$(fdtget -t x "$ROOT/build/dtb/system.dtb" /cpus/cpu@$cpu reg)" = "$cpu"
done
test "$(fdtget "$ROOT/build/dtb/system.dtb" /chosen bootargs)" = \
  'earlycon console=ttyPS0,115200 rdinit=/init rw'
```

DTB 从原工程导出后删除 cpu@3 及对应符号，PMU 中断／affinity 仅保留前三核；不能只将 status 改为 disabled 就假定此厂商 ARM64 枚举路径会排除 CPU3。配置和差异均已归档。本轮没有为裸机增加 carveout。

## 编译四个外部模块

取得上述固定 Xilinx/vcu-modules 提交，可使用原工程缓存或单独源码仓库。VCU_REPO 指向包含该提交的仓库，不能指向未固定版本的工作区。

```bash
VCU_REPO=/path/to/vcu-modules
mkdir -p "$ROOT/staging/vcu-modules"
git -C "$VCU_REPO" archive 844d4c4292e08ad8c3f22ac78e9a937395c1db4b \
  | tar -x -C "$ROOT/staging/vcu-modules"
make -C "$ROOT/src" "${args[@]}" M="$ROOT/staging/vcu-modules" -j4 modules \
  > "$ROOT/logs/external-modules.log" 2>&1
for name in common/allegro al5e/al5e al5d/al5d dmaproxy/dmaproxy; do
  target="$ROOT/staging/modules/lib/modules/$release/extra/$name.ko"
  mkdir -p "$(dirname "$target")"
  "${PREFIX}strip" --strip-debug -o "$target" "$ROOT/staging/vcu-modules/$name.ko"
  /sbin/modinfo -F vermagic "$target"
done
/sbin/depmod -b "$ROOT/staging/modules" -F "$ROOT/build/System.map" "$release"
find "$ROOT/staging/modules/lib/modules/$release" -type f -name '*.ko' | wc -l
```

本轮 58 个内核树内模块和 4 个外部模块，共 62 个；每个 vermagic 应包含正确 release 和 preempt_rt，depmod 不应有未解析符号警告。不要沿用原版模块二进制。

## 保留原 rootfs 元数据并生成 FIT

将原工程 rootfs.cpio.gz、system.dtb 作为输入，不使用普通用户解压再随意重打包的方法。以下复用本轮 newc 变换与 FIT 检查脚本；复制后只替换工作根路径。

```bash
cp "$PROJECT/images/linux/rootfs.cpio.gz" "$ROOT/inputs/"
cp "$PROJECT/images/linux/system.dtb" "$ROOT/inputs/"
for name in BOOT.BIN boot.scr image.ub; do
  cp "$PROJECT/images/linux/$name" "$ROOT/deploy/baseline/$name"
done
for name in pack-rootfs.py cpio_newc.py fdt_read.py validate-fit.py; do
  cp "$REPO/work/scripts/$name" "$ROOT/scripts/"
done
python3 - <<'PY'
import os, pathlib
root = pathlib.Path(os.environ['ROOT'])
for name in ('pack-rootfs.py', 'validate-fit.py'):
    path = root / 'scripts' / name
    path.write_text(path.read_text().replace('/home/wang/p5b-rt-5.4.0', str(root)))
PY
printf '%s\n' "$release" > "$ROOT/logs/kernelrelease.txt"
git -C "$ROOT/src" show -s --format=%ct HEAD > "$ROOT/logs/source-date-epoch.txt"
python3 "$ROOT/scripts/pack-rootfs.py"
gzip -n -9 -c "$ROOT/build/arch/arm64/boot/Image" > "$ROOT/build/arch/arm64/boot/Image.gz"
cp "$REPO/configs/p5b-rt.its" "$ROOT/build/fit/p5b-rt.its"
cp "$ROOT/deploy/baseline/BOOT.BIN" "$ROOT/deploy/rt/"
cp "$ROOT/deploy/baseline/boot.scr" "$ROOT/deploy/rt/"
export SOURCE_DATE_EPOCH=$(cat "$ROOT/logs/source-date-epoch.txt")
mkimage -f "$ROOT/build/fit/p5b-rt.its" "$ROOT/deploy/rt/image.ub"
dumpimage -l "$ROOT/deploy/rt/image.ub"
python3 "$ROOT/scripts/validate-fit.py"
cp "$ROOT/build/.config" "$ROOT/deploy/rt/final.config"
(cd "$ROOT/deploy/baseline"; sha256sum BOOT.BIN boot.scr image.ub > SHA256SUMS)
(cd "$ROOT/deploy/rt"; sha256sum BOOT.BIN boot.scr image.ub final.config > SHA256SUMS)
```

原 rootfs 的 1250 个未替换条目在本轮保留数据及 Unix 元数据，模块与匹配 DTB 被替换；新c脚本带校验。主机工具链、dtc 版本、构建时间、源码提交时间及环境变化可能改变二进制摘要，以上属于过程重建，不声称已在新环境实现逐字节可复现。需要复现本轮完全相同的镜像时使用 Release 的固定 ZIP。

构建清单中保存本轮实测 Image、DTB、ramdisk、FIT 与配置摘要。重新生成后保留自己的配置、日志和摘要，再按根 README 先验证 baseline、后验证 RT。不能将新的构建直接冒认为已保存日志对应的原镜像。
