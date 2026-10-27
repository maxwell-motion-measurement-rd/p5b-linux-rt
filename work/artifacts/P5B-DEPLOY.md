# P5B 首轮 RT Linux SD 启动

状态：2026-10-27 已完成 baseline 基本启动和 RT Core0／1／2 三核首次启动验证。完整流程、实测与原始日志见仓库 README 和 docs/board；实时延迟、完整外设及 AMP 共存尚未验收。目标实板为 P5，软件模型沿用 P5B，完整板级兼容性仍待核对。

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

预期内核版本：5.4.0-rt1-xilinx-v2020.2-p5b；/sys/kernel/realtime 为 1；CPU possible/present/online 均为 0-2。
Linux DTB 的 CPU reg 值应为 0、1、2，且没有 cpu@3。结合完整启动日志确认核心映射，不能只按 CPU 数量判断。
bootargs 应包含 rdinit=/init，不应仍依赖旧的 root=/dev/mmcblk1p2 rootwait。
检查串口、SD、网络及所需驱动。dmaproxy 配置为自动加载；模块加载成功不等同于 DMA 或实际硬件功能已经验证。

## 本轮验证边界

Core3 只做预留，不加载裸机程序。本包没有新增裸机内存分区、共享内存或通信协议。
RT 启动、完整 RT 标志、三核、基本读写和已加载模块检查通过，未完成驱动功能、实时延迟或 AMP 共存验收。实时延迟初测需记录负载、测试工具和条件，正式阈值另行确定。
