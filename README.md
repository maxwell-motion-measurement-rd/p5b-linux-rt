# P5 Linux 5.4.0 PREEMPT_RT 构建与上板验证

截至 2026-10-27，baseline 和 PREEMPT_RT 内核均已从 SD 卡启动。baseline 四核在线；RT 使用 A53 Core0／1／2，完整 RT 状态、基本命令、临时文件读写和已加载模块检查通过。实时延迟、长时间稳定性、完整外设功能及 Core3 裸机共存尚未验收。

目标实板此前已更正为 P5（XCZU4EV），现有 BSP／XSA 和设备树沿用 P5B 工程。日志中的 P5B 是软件模型名称，不是实板识别结果；两版启动成功不代表全部板级配置兼容。仓库、路径和内核版本中的 p5b 保留原名，便于追溯。

## 当前状态

| 检查项 | baseline | RT |
| --- | --- | --- |
| 内核 | `5.4.0-xilinx-v2020.2` | `5.4.0-rt1-xilinx-v2020.2-p5b` |
| SD 启动 | 通过，U-Boot 加载 FIT | 通过，内核／DTB／initramfs 哈希通过 |
| CPU | online 为 0-3 | possible／present／online 均为 0-2，硬件核心标识 0、1、2 |
| 完整 RT | 本轮未按 RT 验收 | CONFIG_PREEMPT_RT=y、realtime=1 |
| 根目录 | 内存 rootfs，参数带旧 root= | 内存 rootfs，使用 rdinit=/init |
| 临时文件读写 | 通过 | 通过 |
| 模块 | 未逐个功能验收 | 构建 62 个；实测加载 dmaproxy、xlnx_vcu_core，未见版本／符号错误 |
| 外设 | 视频、时钟、VCU、无线数据库、SPI NOR 等问题；eMMC FAT 警告 | 相同问题仍在，新增 /dev/root 提示 |
| 实时延迟、AMP | 未测试 | 未测试 |

详细结果见 [baseline 记录](docs/board/baseline-first-boot-20261027.md)和 [RT 记录及问题对照](docs/board/rt-first-boot-20261027.md)。[原始串口日志及 SHA-256](logs/board/2026-10-27/)保留终端命令和输出，不含协作对话。

## 复现入口与所需文件

直接复现本轮上板检查，下载 [board-boot-20261027 Release](https://github.com/nozomiiiii/p5b-linux-rt/releases/tag/board-boot-20261027) 的启动包，无需先重新编译内核。仓库为私有仓库，下载者需要读取权限。

- [p5b-rt-sd-20261027.zip](https://github.com/nozomiiiii/p5b-linux-rt/releases/download/board-boot-20261027/p5b-rt-sd-20261027.zip)
- [ZIP SHA-256](https://github.com/nozomiiiii/p5b-linux-rt/releases/download/board-boot-20261027/p5b-rt-sd-20261027.zip.sha256)
- ZIP 大小：45,463,094 字节。
- SHA-256：`a1a684b678e5eb82a4d04cdbbbdf7e5279792cd257f32674c71b33f285f840a7`。

压缩包保持构建时原始字节；其中旧文档的“待上板”为构建时状态，当前结果以本 README 和 docs/board 为准。

准备匹配的实板、配套电源、PS UART 数据线、SD 卡、读卡器，以及已有 FAT32 启动分区。备份卡内原文件；本轮不需要额外根文件系统分区，不烧写 eMMC／Flash。系统仍会自动挂载板载存储，取卡、断电前应正常关机。

Windows PowerShell 校验并解压：

```powershell
Get-FileHash -LiteralPath '.\p5b-rt-sd-20261027.zip' -Algorithm SHA256
Expand-Archive -LiteralPath '.\p5b-rt-sd-20261027.zip' -DestinationPath '.\p5b-boot-package'
```

包内 baseline/ 为原版，rt/ 为 RT，evidence/ 为构建证据。各启动目录内有 BOOT.BIN、boot.scr、image.ub 和 SHA256SUMS。Linux 主机可在对应目录执行 sha256sum -c SHA256SUMS，Windows 用 Get-FileHash 逐项对照。

两版 BOOT.BIN 和 boot.scr 相同，RT 的变更在 image.ub，包含内核、Linux 设备树与更新匹配模块的 initramfs。

## 串口与 SD 启动设置

1. 将板上 PS UART／USB_UART 调试口连接电脑。本轮为 USB-SERIAL CH340 (COM3)，其他电脑以设备管理器识别的端口为准。
2. MobaXterm 选择 Serial，115200、8 数据位、1 停止位、无校验、无流控，Serial engine 使用 PuTTY。
3. 会话 Terminal settings 启用 Log terminal output to，设置日志目录并重新打开会话。已有文字通过 Terminal → Save terminal text 或 Ctrl + Shift + S 保存。
4. 断电插卡，设置 SD 启动。已核对的 P5B V1.1 手册中 SW6／BOOT_MODE 按 1～4 为 ON、OFF、ON、OFF，SD1 编码 0101。不同板型／底板先核对对应手册，不按图片方向照拨。
5. 若断电后 COM 口消失，先上电、打开串口和日志，再按一次 PS_RST 捕获启动；避免在存储写入时复位。

手册位置：《MPSoC-P5B 之嵌入式 Linux 开发指南 V1.1》第 207–208 页，图 6.3.34／6.3.35；《MPSoC-P5B 开发板用户快速体验 V1.1》第 85 页，图 3.25.1。日志设置见 [MobaXterm 官方文档](https://mobaxterm.mobatek.net/documentation.html)。

## baseline 部署与验证

将 baseline/ 内的 BOOT.BIN、boot.scr、image.ub 直接复制到 FAT32 分区根目录，不能只复制外层目录。安全弹出、断电插卡，上电并记录日志。预期 U-Boot 显示 SD_MODE1，从 mmc1:1 读取 boot.scr 和 FIT，随后进入 Linux root 命令行。

以下命令均在板子串口的 Linux 提示符下逐行执行，不在主机或 U-Boot 中执行：

```sh
uname -a
cat /proc/cmdline
cat /sys/devices/system/cpu/online
cat /proc/meminfo | head -n 5
mount
df -h
uptime
echo p5b-baseline-ok > /tmp/p5b-baseline-check.txt
cat /tmp/p5b-baseline-check.txt
rm /tmp/p5b-baseline-check.txt
dmesg
```

关键结果：原版 5.4.0-xilinx-v2020.2、CPU online 0-3、约 4 GB 内存，读回 p5b-baseline-ok。本次 MemTotal=4029560 kB，采样时运行约 11 分钟。时间、地址、可用内存和部分启动顺序可能变化，不要求逐行相同。

本次 / 实际为 rootfs，不能仅凭启动参数中的 root=/dev/mmcblk1p2 判断根文件系统位置。保存为 baseline-first-boot.txt，与[原始日志](logs/board/2026-10-27/baseline-first-boot.txt)对照。

## RT 部署与验证

baseline 结果保存后，在板端执行：

```sh
sync
poweroff
```

关机完成后关闭电源并取卡。备份 SD 原文件，以 rt/ 内三件套覆盖根目录同名文件。不要只更新散放的 Image／system.dtb，当前脚本实际加载 image.ub。安全弹出、插回、上电，另存新一轮日志。

进入 Linux 后执行：

```sh
uname -a
cat /sys/kernel/realtime
cat /sys/devices/system/cpu/possible
cat /sys/devices/system/cpu/present
cat /sys/devices/system/cpu/online
cat /proc/cmdline
zcat /proc/config.gz | grep -E '^CONFIG_(PREEMPT_RT|NR_CPUS)='
ls /lib/modules
ls /proc/device-tree/cpus
grep '^processor' /proc/cpuinfo
lsmod
echo p5b-rt-ok > /tmp/p5b-rt-check.txt
cat /tmp/p5b-rt-check.txt
rm /tmp/p5b-rt-check.txt
mount
cat /etc/fstab
cat /proc/meminfo | head -n 5
uptime
command -v cyclictest
command -v stress-ng
command -v stress
command -v taskset
command -v chrt
grep -nE '/dev/root|mount.*remount|mount -a' /etc/init.d/* /etc/init.d/.* 2>/dev/null
dmesg
```

关键实测结果：

```text
内核：5.4.0-rt1-xilinx-v2020.2-p5b，SMP PREEMPT_RT
/sys/kernel/realtime：1
possible / present / online：0-2 / 0-2 / 0-2
CONFIG_PREEMPT_RT=y
CONFIG_NR_CPUS=3
bootargs：earlycon console=ttyPS0,115200 rdinit=/init rw
CPU 节点：cpu@0 cpu@1 cpu@2，没有 cpu@3
processor：0、1、2
模块：dmaproxy、xlnx_vcu_core
临时文件读回：p5b-rt-ok
根挂载：rootfs on / type rootfs
MemTotal：4025676 kB
```

启动日志确认 CPU0 物理标识 0x0、CPU1 为 0x1、CPU2 为 0x2，共三个 CPU。保存为 rt-first-boot.txt，与[原始日志](logs/board/2026-10-27/rt-first-boot.txt)对照。

本次 PATH 中未找到上述五个测试／调度命令，没有运行 cyclictest 或负载测试。realtime=1 不代表实时延迟达标；模块加载不代表 DMA、VCU 数据通路通过。正常关机后再断电。

## 已知问题与回退

- 两版均有视频缩放桥 Invalid height in dt／-22、MIPI 解析失败，以及 VCU、时钟、无线数据库、SPI NOR JEDEC ID 等问题。帧缓存和 CSC 的部分早期 -517 后续重试成功，不能一概算作最终失败。
- RT 新增 /dev/root: Can't open blockdev。实际根为内存 rootfs，而 fstab 仍保留 /dev/root，启动脚本也重新挂载根目录；具体触发路径未完全定位，本轮未修改。
- eMMC FAT 分区未正常卸载警告尚未离线检查或修复。两版能启动不证明存储无损坏。
- 保存日志中未见 panic、Oops、Call trace、BUG；RT 未见模块版本或未知符号错误。结论仅覆盖保存的阶段。

完整对照见 [RT 记录](docs/board/rt-first-boot-20261027.md)。回退时正常关机、断电并恢复 baseline/ 三件套；若 RT 无响应，先保存输出、确认没有烧写操作，再断电恢复。[回退说明](work/artifacts/P5B-ROLLBACK.md)列出分阶段排查方法。

## 为什么不用 Linux 4.9 的 RT 补丁

本工程为 Xilinx 2020.2 / Linux 5.4.0。PREEMPT_RT 补丁对应特定源码基线，涉及锁、中断、调度、定时器和架构代码；4.9 补丁不能直接作为 5.4.0 的通用补丁。改用 4.9 还需选择、适配对应内核、BSP、驱动、设备树与固件。本轮没有做 4.9 降级／移植，也没有证据认定其性能更差。

本轮保留厂商 5.4.0，固定使用 RETIS 的 patch-5.4.3-rt1.patch 作为移植输入。在指定厂商提交上零失败、零 fuzz 应用后，完成编译、打包及本次 RT 三核启动。文件名中的 5.4.3 不代表任意 5.4.0 都适用，也不表示本内核已升级为 5.4.3。固定版本、选择依据和来源见 [ADR 0001](docs/adr/0001-preserve-vendor-kernel-baseline.md)。

## 源码重建与目录

[源码重建说明](docs/build/REPRODUCE.md)给出固定版本、原 BSP／工具链前提、命令与打包顺序；[Git 备份说明](docs/build/kernel-git-backup.md)说明如何恢复内核提交。直接上板使用 Release 包；源码重建还需原工程输入，本仓库不含完整 BSP。

| 路径 | 内容 |
| --- | --- |
| docs/board/、logs/board/ | 两版板端记录、原始日志 |
| docs/build/ | 重建说明、清单、静态校验、Git 备份 |
| docs/adr/、docs/plans/ | 技术决策、构建流程、阶段状态 |
| configs/ | 原配置、RT 配置、三核 DTS、FIT ITS |
| patches/ | 内核提交补丁、bundle、设备树差异 |
| work/inputs/ | 固定原始 RT 补丁 |
| work/scripts/ | 原环境构建、打包、检查脚本 |
| work/artifacts/ | 部署／回退说明、ZIP 校验值 |

构建清单中 hardware_boot_verified=false 保留构建时状态；当前实测以 docs/board 为准。脚本的本机路径属于环境参数，不是共享服务地址。仓库不保存 SSH 私钥、连接配置或协作对话；源码和脚本保留各自许可。
