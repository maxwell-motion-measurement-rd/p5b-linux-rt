# baseline 首次 SD 启动与基本检查

记录日期：2026-10-27。依据用户保存的串口日志及本轮检查命令输出整理。

原版 Linux 已从 SD 启动，进入 root 命令行，四个 A53 核在线，内存可见，临时文件读写正常。本轮基本启动检查通过。视频处理链路中有明确的驱动初始化失败，另有时钟、VCU、无线数据库和文件系统警告，不能将结果写成全部外设已通过验收。

## 板型与记录范围

仓库此前已将目标实板更正为 P5（XCZU4EV）；本次沿用 P5B 工程的 baseline。U-Boot 和 Linux 的设备树模型仍为 `Alientek MpSoc-P5B Development Board`。日志中的名称来自软件配置，不能代替实板型号识别，也不能证明 P5／P5B 的全部板级配置兼容。仓库与启动包中的 `p5b` 名称继续保留，便于追溯。

日志从 U-Boot 开始，包含 FIT 加载、Linux 和用户空间启动、用户操作、检查命令，以及再次输出的完整 dmesg。开头有少量乱码；未包含完整 FSBL／PMUFW 早期输出，也不是连续的长时间稳定性测试。

记录日期使用本轮实际工作日期。日志中的 RTC 时间和镜像编译日期保持原文，不作为本次测试日期。

## 原始证据

- Windows 原文件：`D:\P5B_logs\baseline-first-boot.txt`。
- 仓库副本：[baseline-first-boot.txt](../../logs/board/2026-10-27/baseline-first-boot.txt)。
- 文件大小：65,249 字节。
- SHA-256：`41cd0d2c7122b02ad0d82d67dd0bf8adb7013d653fb1c4a32f80ac813e4fcf9b`。
- [校验文件](../../logs/board/2026-10-27/baseline-first-boot.txt.sha256)。

日志按原字节归档，不润色、不删减、不转换换行。本文仅整理结果，原始错误以日志为准。启动三件套尚未在板端重新计算哈希，因此不声称已完成板端文件与交付包逐字节核对。

## 启动路径

U-Boot 输出 `Bootmode: SD_MODE1`，选择 `mmc1`，扫描 `1:1` 分区，执行 `/boot.scr` 并加载 FIT。内核、ramdisk 和设备树的 FIT 哈希检查通过，Linux 随后执行 `/init`，用户空间完成启动并进入 `root@ALIENTEK-MP` 提示符。

日志识别的器件为 `zu4ev`，DRAM 为 `4 GiB`。

## 基本检查结果

| 检查 | 实测结果 | 本轮结论 |
| --- | --- | --- |
| `uname -a` | `Linux ALIENTEK-MP 5.4.0-xilinx-v2020.2 #1 SMP Tue Oct 20 06:24:36 UTC 2026 aarch64 GNU/Linux` | 已启动原版 AArch64 SMP 内核 |
| CPU online | `0-3` | 四核在线；尚未切换为 RT 三核配置 |
| 内存 | `MemTotal: 4029560 kB`，`MemAvailable: 3875356 kB` | 本次采样可见约 3.84 GiB 总内存 |
| 运行时间 | `up 11 min`，负载 `0.00, 0.00, 0.00` | 该采样点系统已运行约 11 分钟，不代表长时间稳定性通过 |
| 临时文件 | `/tmp` 写入、读回 `p5b-baseline-ok`，随后删除 | 基本临时文件读写通过，不代表持久化存储验收 |
| 内核崩溃 | 所提供日志未见 Kernel panic、Oops 或 Call trace | 本轮没有观察到对应崩溃报告 |
| USB | 识别 GenesysLogic USB2.0 Hub 和 USB3.0 Hub | Hub 枚举已发生，数据传输功能未测试 |
| 网络 | DHCP 输出 `no lease, forking to background` | 本轮未获取租约，网络连通性未通过验证 |

### 根文件系统与存储

启动参数为：

```text
earlycon console=ttyPS0,115200 root=/dev/mmcblk1p2 rw rootwait
```

实际根挂载为：

```text
none on / type rootfs (rw)
```

FIT 内含 ramdisk，内核执行 `/init`，实际 `/` 为 rootfs；本次未将 `mmcblk1p2` 挂载为根目录。日志中 SD `mmcblk1` 也只列出 `p1`，因此不能按启动参数认定系统运行在 SD 第二分区。

日志将 `mmcblk0` 识别为 7.28 GiB MMC，将 `mmcblk1` 识别为 29.8 GiB SDHC。当前自动挂载了：

| 分区 | 挂载位置 | 类型 |
| --- | --- | --- |
| `/dev/mmcblk0p2` | `/media/sd-mmcblk0p2` | ext4 |
| `/dev/mmcblk0p1` | `/media/sd-mmcblk0p1` | vfat |
| `/dev/mmcblk1p1` | `/media/sd-mmcblk1p1` | vfat |

这些挂载说明即使根文件系统在内存中，eMMC 和 SD 分区仍会被系统挂载。后续取卡或断电前要正常关机。

## 已观察到的问题

以下均出现在 baseline 中，不能归因于尚未启动的 RT 内核。根因尚未完成源码、设备树和硬件设计的联合核查。

| 对象 | 日志证据 | 当前判断与范围 |
| --- | --- | --- |
| 视频帧缓存读写、色彩转换、缩放模块 | 获取 `ap_clk`、`aclk`、`aclk_axis` 等资源时返回 `-517` | 表示依赖未就绪、请求延迟探测；仅凭早期这几行不能认定最终失败 |
| 视频缩放桥与 MIPI 采集链路 | `parse_of failed`、DMA 初始化和 graph 解析失败，最终 `probe ... failed with error -22` | 对应驱动在本次启动中初始化失败，摄像头及该视频链路未通过功能验收 |
| PL／PLL 时钟操作 | `pl2_ref_div1` 分频设置、`dpll_int` 关闭返回 `-13` | 相关操作被拒绝，具体权限、固件或配置原因待查；不能推断全部时钟失效 |
| USB DWC3 | `Failed to get clk 'ref': -2` | 未找到命名时钟资源；后续仍识别 USB2／USB3 Hub，不能据此判定 USB 全部不可用 |
| VCU | 三次 `failed to get reset gpio for vcu` | 获取复位 GPIO 时出错，未完成最终驱动绑定和编解码功能核查 |
| 无线监管数据库 | `regulatory.db` 加载返回 `-2` | 数据库文件未成功加载；不表示有线网口故障，也不证明安装了 Wi-Fi 模块 |
| eMMC 文件系统 | `mmcblk0p2: recovery complete`；`mmcblk0p1: Volume was not properly unmounted. Some data may be corrupt. Please run fsck.` | ext4 报告已完成恢复，FAT 分区存在未正常卸载警告；未执行离线检查，不能声称没有损坏或已经修复 |
| mtdoops | `mtd device ... must be supplied` | 崩溃日志组件未指定保存分区，不等于 Flash 损坏 |
| dmaproxy | `loading out-of-tree module taints kernel` | 外部模块已加载；这条提示本身不代表模块加载失败，也不证明 DMA 数据通路已验证 |

看门狗的 `timeout 10s` 是超时配置报告，不是发生超时的证据。用户执行 `rm -h` 后的 BusyBox 参数错误也不是内核故障。

## 下一步与验收边界

1. 保留 baseline 启动文件和原始日志，作为 RT 对照。
2. 正常关机、断电后切换 RT 启动三件套，记录新一轮串口日志。
3. 核对 RT 内核版本 `5.4.0-rt1-xilinx-v2020.2-p5b`、`/sys/kernel/realtime=1`、CPU possible／present／online 均为 `0-2`，并核对设备树核心映射、内嵌配置和匹配模块。
4. 比较 baseline 与 RT 的启动差异，区分原有外设问题与新增问题。使用相关外设前逐项定位和验收；eMMC FAT 分区警告需在备份后安排离线文件系统检查，本轮没有执行修复。
5. RT 启动通过后，再开展驱动回归和带明确负载条件的实时延迟测试。Core3 裸机、AMP 共存和通信仍属于后续阶段。

本轮不宣称已通过 RT、三核、实时性能、全部外设或 P5／P5B 全部板级兼容性验收。
