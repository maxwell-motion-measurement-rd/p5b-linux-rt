import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess
import zipfile

root = pathlib.Path('/home/wang/p5b-rt-5.4.0')
assert (root/'logs/step6.complete').is_file()
rt = root/'deploy/rt'
baseline = root/'deploy/baseline'
evidence = root/'deploy/evidence'
evidence.mkdir(exist_ok=True)
release = (root/'logs/kernelrelease.txt').read_text().strip()

def digest(path):
    result = hashlib.sha256()
    with pathlib.Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()

def write(path, text):
    path.write_text(text, encoding='utf-8')

shutil.copy2(str(root/'build/.config'), str(rt/'final.config'))
assert (root/'logs/Image.embedded.config').read_bytes() == (rt/'final.config').read_bytes()
fit = json.loads((root/'logs/fit-validation.json').read_text())
rootfs = json.loads((root/'logs/rootfs-validation.json').read_text())
manifest = {
    'prepared_at': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
    'hardware_boot_verified': False,
    'target_xsa_part': 'xczu4ev-sfvc784-2-i',
    'target_board': 'Alientek MpSoc-P5B Development Board',
    'source_commit': '62ea514294a0c9a80455e51f1f4de36e66e8c546',
    'kernelrelease': release,
    'architecture': 'AArch64', 'linux_core_reg_values': [0, 1, 2],
    'embedded_kernel_config_matches_delivered_config': True,
    'core3': 'Excluded from this Linux DTB; no bare-metal payload included',
    'patch': {'repository': 'fred-framework/meta-retis',
              'commit': '02995952c2df1819657f2998e6e3a63c0e2aaa63',
              'path': 'recipes-kernel/linux/files/patch-5.4.3-rt1.patch',
              'sha256': digest(root/'inputs/patch-5.4.3-rt1.patch')},
    'external_module_source': {'repository': 'xilinx/vcu-modules',
                               'commit': '844d4c4292e08ad8c3f22ac78e9a937395c1db4b',
                               'modules': ['allegro', 'al5e', 'al5d', 'dmaproxy'],
                               'archive_sha256': digest(root/'inputs/vcu-modules-source.tar')},
    'compiler': 'aarch64-xilinx-linux-gcc 9.2.0',
    'binutils': '2.32.0.20190204',
    'build_warnings': [
        'drivers/of/configfs.c:46: unused overlay_lock (vendor source unchanged)',
        'vcu-modules/common/al_mailbox.c:146: variable-length array header',
        'vcu-modules/common/al_mailbox.c:172: variable-length array header'],
    'boot_chain': 'Original BOOT.BIN and boot.scr preserved byte for byte',
    'fit': fit, 'rootfs': rootfs,
    'boot_file_sha256': {name: digest(rt/name) for name in ('BOOT.BIN', 'boot.scr', 'image.ub')},
    'final_config_sha256': digest(rt/'final.config'),
}
write(rt/'build-manifest.txt', json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
write(rt/'DEPLOY.md', '''# P5B 首轮 RT Linux SD 启动

状态：已完成主机构建和包内静态校验；尚未经实际 P5B 启动验证。

## 使用前核对

1. 核对板卡、硬件版本与本工程 XSA/BSP 是否匹配。本工程 XSA 声明 xczu4ev-sfvc784-2-i，PetaLinux/Vivado 2020.2。
2. 按实际 P5B 手册确认 SD 启动拨码、SD 插槽和串口。不要照搬其他开发板拨码。
3. 保留 SD 原有启动文件；本包不要求格式化卡，也不写入板载 Flash。
4. BOOT.BIN 包含原工程的启动固件及 PL 位流。若硬件导出与到手板卡不匹配，先取得匹配的基线。

## 文件复制

将 rt 目录中的 BOOT.BIN、boot.scr、image.ub 三个文件一起复制到已准备好的 FAT32 启动分区根目录。
final.config、build-manifest.txt、校验文件和文档属于构建记录，不需要作为启动文件复制。
使用 Linux 主机复制时可执行 sha256sum -c SHA256SUMS 验证完整的 rt 目录；Windows 可用 Get-FileHash 对照清单。
不要只复制散放的 Image 或 system.dtb：当前 boot.scr 优先加载 image.ub，实际内核、Linux DTB、initramfs 都在新 FIT 中。
首轮使用内存中的 initramfs 根文件系统，不要求把 rootfs 解压到 SD 第二分区。对内存根文件系统的普通修改重启后不会保存。

## 首次启动顺序

1. 建议先保存原版 baseline 三件套的启动结果，再切换为 rt 三件套，以区分原有硬件/固件问题和 RT 变更。
2. 断电放卡并设置经手册核对的启动方式，串口使用 115200 8N1，保存完整上电日志。
3. 上电后记录 FSBL、U-Boot、Linux、用户空间分别是否启动。若需诊断，可在 U-Boot 倒计时时中断自动启动；先读取当前环境，不随意保存环境或改写 Flash。

## 进入 Linux 后核对

```sh
uname -r
cat /sys/kernel/realtime
cat /sys/devices/system/cpu/possible
cat /sys/devices/system/cpu/present
cat /sys/devices/system/cpu/online
cat /proc/cmdline
zcat /proc/config.gz | grep -E 'CONFIG_(PREEMPT_RT|NR_CPUS|ARM64|ARCH_ZYNQMP)='
ls /proc/device-tree/cpus
lsmod
dmesg
```

预期内核版本：RELEASE_PLACEHOLDER；/sys/kernel/realtime 为 1；CPU possible/present/online 均为 0-2。
Linux DTB 的 CPU reg 值应为 0、1、2，且没有 cpu@3。结合完整启动日志确认核心映射，不能只按 CPU 数量判断。
bootargs 应包含 rdinit=/init，不应仍依赖旧的 root=/dev/mmcblk1p2 rootwait。
检查串口、SD、网络及所需驱动。dmaproxy 配置为自动加载；模块加载成功不等同于 DMA 或实际硬件功能已经验证。

## 本轮验证边界

Core3 只做预留，不加载裸机程序。本包没有新增裸机内存分区、共享内存或通信协议。
尚未验证实际启动、驱动运行、RT 延迟或 AMP 共存。实时延迟初测需记录负载、测试工具和条件，正式阈值另行确定。
'''.replace('RELEASE_PLACEHOLDER', release))
write(rt/'ROLLBACK.md', '''# 恢复原版启动文件

baseline 目录保存了原工程的 BOOT.BIN、boot.scr 和 image.ub，并有独立 SHA256SUMS。
这些文件已与原工程逐字节核对，但尚未经本次实际板卡启动验证。

1. 断电后将 SD 卡接回主机，备份当前卡上的三个启动文件。
2. 将 baseline 中的 BOOT.BIN、boot.scr、image.ub 三件套恢复到同一启动分区根目录，避免混用两套文件。
3. 按板卡手册确认启动方式，再上电保存完整日志。

若原版和 RT 版都无法进入 U-Boot，优先核对供电、启动介质、拨码、串口及硬件/BSP匹配。
若能进入 U-Boot 但不能启动内核，记录加载路径、FIT读取和启动错误。
若 Linux 启动后报错，保存完整内核日志与实际版本，检查根文件系统、CPU和模块状态。
本流程不涉及改写板载 Flash。
''')
write(root/'deploy/README.md', '''# P5B RT Linux 首轮 SD 启动文件包

- rt/：新 RT 系统三件套及配置、校验、部署/回退说明。
- baseline/：原工程三件套及校验，用作回退候选；未在本次实际板卡验证。
- evidence/：补丁、配置差异、设备树修改、构建日志和验证结果。

部署时先阅读 rt/DEPLOY.md。只选择一套三件套复制到 SD 启动分区，不能把 rt 和 baseline 的文件混合。
当前交付是完成主机构建并经过静态校验的待上板包，不代表已经在板端运行或通过实时性验收。
''')

selected = ['step1-baseline.log', 'patch-dry-run.log', 'patch-apply.log',
            'patch-reverse-check.log', 'patch-diff-stat.txt', 'rt-applied.diff',
            'config-diff.final.txt', 'dtb-changes.diff', 'kernel-build.log',
            'modules-install.log', 'step5-external-modules.log', 'depmod.log',
            'kernelrelease.txt', 'kernel-artifacts.sha256', 'modules-built.txt',
            'fit-listing.txt', 'fit-validation.json', 'rootfs-validation.json',
            'step5-started.txt', 'step5-finished.txt', 'build-paths.txt',
            'step3-toolchain-refine.log', 'step4-dtb.log',
            'boot-script.txt', 'u-boot-default-environment.txt', 'Image.embedded.config']
for name in selected:
    source = root/'logs'/name
    assert source.is_file(), source
    shutil.copy2(str(source), str(evidence/name))
shutil.copy2(str(root/'inputs/patch-5.4.3-rt1.patch'), str(evidence/'patch-5.4.3-rt1.patch'))
shutil.copy2(str(root/'build/dtb/p5b-rt.dts'), str(evidence/'p5b-rt.dts'))
shutil.copy2(str(root/'build/fit/p5b-rt.its'), str(evidence/'p5b-rt.its'))
script_target = evidence/'scripts'
script_target.mkdir(exist_ok=True)
for source in sorted((root/'scripts').iterdir()):
    if source.is_file() and source.suffix in ('.sh', '.py'):
        shutil.copy2(str(source), str(script_target/source.name))
for directory in (rt, baseline):
    files = sorted(path for path in directory.iterdir() if path.is_file() and path.name != 'SHA256SUMS')
    write(directory/'SHA256SUMS', ''.join('%s  %s\n' % (digest(path), path.name) for path in files))
    subprocess.check_call(['sha256sum', '-c', 'SHA256SUMS'], cwd=str(directory))

original = pathlib.Path('/home/wang/petalinux/ALIENTEK-MP/components/yocto/workspace/sources/linux-xlnx')
assert subprocess.check_output(['git', '-C', str(original), 'rev-parse', 'HEAD']).decode().strip() == manifest['source_commit']
status = subprocess.check_output(['git', '-C', str(original), '--no-optional-locks', 'status', '--porcelain=v1', '--untracked-files=all'])
assert status == (root/'logs/original-source-status.txt').read_bytes()
for name in ('BOOT.BIN', 'boot.scr', 'image.ub'):
    assert digest(baseline/name) == digest(pathlib.Path('/home/wang/petalinux/ALIENTEK-MP/images/linux')/name)

archive_path = root/'deploy/p5b-rt-sd-20261027.zip'
with zipfile.ZipFile(str(archive_path), 'w', zipfile.ZIP_DEFLATED) as archive:
    for folder in (rt, baseline, evidence):
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                archive.write(str(path), path.relative_to(root/'deploy').as_posix())
    archive.write(str(root/'deploy/README.md'), 'README.md')
with zipfile.ZipFile(str(archive_path), 'r') as archive:
    assert archive.testzip() is None
    assert archive.read('rt/image.ub') == (rt/'image.ub').read_bytes()
    assert archive.read('baseline/image.ub') == (baseline/'image.ub').read_bytes()
archive_hash = digest(archive_path)
write(root/'deploy/p5b-rt-sd-20261027.zip.sha256', archive_hash + '  ' + archive_path.name + '\n')
(root/'logs/step7.complete').touch()
print('DELIVERY_OK path=%s bytes=%d sha256=%s' % (archive_path, archive_path.stat().st_size, archive_hash))
