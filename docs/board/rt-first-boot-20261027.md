# RT 首次 SD 启动、三核验证与 baseline 对照

记录日期：2026-10-27。依据原始串口日志整理，RT 部署与验证在 P5（XCZU4EV）实板上完成。软件沿用 P5B 工程名称；现有资料检索未发现与本次部署相关的明显差异，范围见[板型说明](p5-and-p5b-scope.md)。

## 结论与原始证据

RT 内核已从 SD 启动到 root 命令行。版本、完整 RT 配置和运行标志一致；Linux 使用 A53 Core0／1／2，基本临时文件读写通过，dmaproxy 和 xlnx_vcu_core 已加载。实时延迟、长时间稳定性、完整外设功能及 Core3 裸机共存尚未测试。

- 原文件：`D:\P5B_logs\rt-first-boot.txt`。
- [仓库原始日志](../../logs/board/2026-10-27/rt-first-boot.txt)，71,950 字节。
- SHA-256：`67b11c178f048afd4770c567333b2736c0a99e30ce00793ddb91a29a6109eba9`。
- [校验文件](../../logs/board/2026-10-27/rt-first-boot.txt.sha256)。
- 对照：[baseline 记录](baseline-first-boot-20261027.md)和 [baseline 日志](../../logs/board/2026-10-27/baseline-first-boot.txt)。

日志保留原字节、开头乱码及交错回显，包含 U-Boot、Linux、检查命令与再次输出的 dmesg；不含完整 FSBL／PMUFW 早期输出。日志内 RTC 时间和编译日期不作为本次测试日期。

## 部署与 FIT 校验

baseline 结果保存后正常关机、断电、取卡，备份原版文件。以 rt 目录的 BOOT.BIN、boot.scr、image.ub 覆盖 SD FAT32 根目录同名文件，安全弹出、插回并记录启动。两版共用原 BOOT.BIN 和 boot.scr；RT 的内核、三核 Linux DTB 和匹配模块 initramfs 都在新 image.ub 中。没有新增裸机载荷、共享内存或外设隔离配置。

可复制的完整部署与检查命令见 [README](../../README.md)。U-Boot 显示 SD_MODE1，从 mmc1:1 加载 /boot.scr 和 19,501,100 字节的 image.ub。三个载荷均显示 sha256+ OK，摘要与构建清单一致：

| 载荷 | 字节数 | SHA-256 |
| --- | --- | --- |
| gzip 内核 | 8,369,434 | `ef40de3bb4a906c605b2dfc83c3e5183b14c72736437bff44b0febc685343b58` |
| Linux DTB | 54,064 | `1d0528ef851e6efc3e43f031a7bac132ebf130d6c9df6a753f1bb393c58396a4` |
| initramfs | 11,075,497 | `f07764dbbea5733556bc0e336a0fafdda7ebc3eb605ee96449ac852b6bc7f574` |

以上证明加载的 FIT 载荷与构建记录对应；本轮没有在板端重新读取整个 SD 三件套计算哈希。

## 验证过程与输出

| 检查 | 实测 |
| --- | --- |
| uname -a | 5.4.0-rt1-xilinx-v2020.2-p5b，SMP PREEMPT_RT，AArch64 |
| /sys/kernel/realtime | 1 |
| CPU possible／present／online | 均为 0-2 |
| 内嵌配置 | CONFIG_PREEMPT_RT=y、CONFIG_NR_CPUS=3 |
| 启动参数 | earlycon console=ttyPS0,115200 rdinit=/init rw |
| /lib/modules | 与运行版本同名目录 |
| /proc/device-tree/cpus | cpu@0、cpu@1、cpu@2，无 cpu@3 |
| /proc/cpuinfo | processor 0、1、2 |
| lsmod | dmaproxy、xlnx_vcu_core；未见版本或未知符号错误 |
| /tmp 写入、读回、删除 | 读回 p5b-rt-ok，命令完成 |
| mount | rootfs on / type rootfs (rw,size=1876072k,nr_inodes=469018) |
| 内存 | MemTotal=4025676 kB，MemAvailable=3919476 kB |
| uptime | 采样时 up 6 min，负载 0.00、0.08、0.05 |
| 工具检查 | PATH 中未找到 cyclictest、stress-ng、stress、taskset、chrt |

启动日志进一步确认核心映射：

```text
Booting Linux on physical CPU 0x0000000000
CPU1: Booted secondary processor 0x0000000001
CPU2: Booted secondary processor 0x0000000002
smp: Brought up 1 node, 3 CPUs
SMP: Total of 3 processors activated.
```

Linux 没有启动 CPU3；不代表 CPU3 已运行裸机，也不代表裸机所需资源已经隔离。62 个模块构建完成不等于 62 个模块已上板逐一测试；模块加载也不代表对应数据通路可用。

## 与 baseline 的问题对照

对比去除了时间戳和 RT 的 CPU 编号前缀。错误／警告类消息中新增 /dev/root: Can't open blockdev；这不代表所有日志完全相同，也不覆盖未记录阶段。

| 对象 | 对照结果 |
| --- | --- |
| 帧缓存／CSC | 两版早期均有 -517，后续均报告 FrameBuffer Driver Probed、CSC driver probed；这些延迟探测后来成功 |
| 视频缩放桥 | 两版均有 Invalid height in dt、parse_of failed 和 -22；同地址的 VPSS Scaler 驱动随后报告 Probe Successful，需区分驱动 |
| MIPI 视频采集 | 两版均有 DMA／graph 初始化失败，完整链路未验证 |
| PL／PLL 时钟 | 两版 pl2_ref_div1、dpll_int 操作均返回 -13 |
| VCU | 两版均有 reset GPIO 报错；RT 模块已加载，但设备绑定及编解码未核验 |
| USB | 两版均缺 DWC3 ref 时钟资源，后续均识别 USB2／USB3 Hub，未测数据传输 |
| SPI NOR | 两版均报 unrecognized JEDEC id bytes: ef 60 19 00 00 00，Flash 识别及读写未通过验收 |
| 显示 | 两版均有 Cannot find any crtc or sizes 等信息，显示功能未测试 |
| 无线／网络 | 两版均缺 regulatory.db，DHCP 未拿到租约；不据此认定有线硬件损坏 |
| eMMC | 两版 mmcblk0p1 均有 FAT 未正常卸载警告；baseline ext4 做过恢复，RT ext4 报告挂载；未离线修复 |
| 内核／模块 | 保存日志未见 panic、Oops、Call trace、BUG；RT 未见模块版本／未知符号错误；外部模块 taint 提示不等于加载失败 |

### RT 新增根设备提示

```text
/dev/root: Can't open blockdev
```

提示在执行 /init 后出现，系统随后完成启动。实际根目录为内存 rootfs，/etc/fstab 仍保留：

```text
/dev/root            /                    auto       defaults              1  1
```

脚本检索发现 checkroot.sh 第 84、142 行重新挂载根目录，mountall.sh 第 20 行执行 mount -at nonfs,nosmbfs,noncpfs。这支持沿用的根挂载配置与 initramfs 方案不一致的排查方向；具体触发路径尚未完全定位。本轮没有修改 fstab、脚本或重新打包。

## 本轮结束状态

baseline 基本启动与 RT 三核首次启动通过，记录和原始日志已归档。实时延迟、测试工具部署、长时间稳定性、外设修复及 AMP 通信留待后续，本轮没有执行。板型与软件模型的区别沿用 README 的说明，启动成功不代表全部板级适配完成。
