# SD 部署与启动核验

本指南用于复现已发布的 baseline／原始 RT 启动包。下面的 Release 只提供 baseline／原始 RT，没有诊断镜像下载；ftrace／PMU 测试需按[诊断构建步骤](build/REPRODUCE.md#从原始流程生成诊断内核)自行准备独立镜像和工具。测试范围见[测试方法与结果](reports/rt-assessment-summary-20261029.md)。

## 1. 准备与校验

需要匹配的 P5 实板、电源、PS UART、SD 卡与读卡器；已有 FAT32 启动分区即可，本包以 initramfs 为运行根文件系统，不需要额外 EXT4 根分区。核对实际板型、载板修订与硬件设计；不能只凭软件中的 P5B 名称认板。

从 [Release](https://github.com/nozomiiiii/p5b-linux-rt/releases/tag/board-boot-20261027) 下载 `p5b-rt-sd-20261027.zip` 及其 `.sha256`。ZIP 为 45,463,094 字节，SHA-256：

```text
a1a684b678e5eb82a4d04cdbbbdf7e5279792cd257f32674c71b33f285f840a7
```

Linux 使用 `sha256sum`，PowerShell 使用 `Get-FileHash -Algorithm SHA256`。在新目录解压，分别核对 `baseline/`、`rt/` 的 SHA256SUMS。旧包内“待上板”是打包时状态，当前结果以仓库测试总结为准。

## 2. 认识启动文件

| 文件 | 用途 |
| --- | --- |
| BOOT.BIN | 早期启动组件及 U-Boot；硬件设计变化时需重新核对 |
| boot.scr | U-Boot 启动脚本；本包 SD 分支加载 image.ub 后执行 bootm |
| image.ub | FIT 镜像：内核、Linux DTB、initramfs；RT 模块位于 initramfs 中 |

baseline 与原始 RT 的 BOOT.BIN、boot.scr 相同，变更集中在 image.ub。采用这套 FIT 布局时，单独替换散放的 Image 不会更新 FIT 内的内核。模块必须匹配内核 release；更换 XSA／DDR／PL 或固件时，不能继续假定早期启动文件兼容。

## 3. 启动 baseline，再切换 RT

1. 备份 SD 中的原始三件套及摘要。正常关机后断电取卡，将 `baseline/` 的 BOOT.BIN、boot.scr、image.ub 直接复制到启动分区根目录，读回校验并安全弹出。
2. 连接 PS UART：115200、8N1、无流控，打开日志。串口号按主机实际识别选择，任一时刻只由一个程序占用。
3. 按对应硬件手册选择 SD 启动。P5B V1.1 文档的 SW6 第 1—4 位为 ON、OFF、ON、OFF；其他载板先核对手册与拨码方向。上电记录启动日志。
4. baseline 应进入 Linux，`uname -r` 为 `5.4.0-xilinx-v2020.2`，CPU online 为 `0-3`。先排除基本启动故障。
5. 板端执行 `sync`、`poweroff`，确认关机后断电取卡；用 `rt/` 三件套替换，读回校验、安全弹出后重新启动。

手册来源：《MPSoC-P5B 之嵌入式 Linux 开发指南 V1.1》207—208 页，以及《开发板用户快速体验 V1.1》85 页；使用时应核对随板版本。

## 4. RT 运行核验

以下命令在开发板 Linux 中执行：

```sh
uname -r
cat /sys/kernel/realtime
cat /sys/devices/system/cpu/possible
cat /sys/devices/system/cpu/present
cat /sys/devices/system/cpu/online
zcat /proc/config.gz | grep -E 'CONFIG_PREEMPT_RT=|CONFIG_NR_CPUS='
ls /lib/modules
lsmod
dmesg
```

原始 RT 预期 release 为 `5.4.0-rt1-xilinx-v2020.2-p5b`、realtime 为 1、三组 CPU 集合均为 0-2、PREEMPT_RT=y、NR_CPUS=3，模块目录与 release 一致。本次共构建 62 个模块，实测加载 dmaproxy、xlnx_vcu_core，未逐一验收全部模块。Core3 尚未启动裸机；三核枚举不等于 AMP 已实现。

原始 RT image.ub SHA-256 为 `f7c224640ad30359a731a5492f06769b4f081496c88fbe273022c48fd2789484`。核对镜像摘要、版本、配置与串口日志，避免只看版本字符串。

## 5. 排障与回退

按“早期固件 → U-Boot → FIT 加载 → 内核 → 用户空间”定位停止阶段，保存完整日志。原环境仍有视频、时钟、VCU、SPI NOR、eMMC FAT 和 /dev/root 提示；能启动不代表这些外设已通过功能验收。

需要回退时正常关机、断电，恢复已校验的原三件套。由诊断版恢复原始 RT 时，也需恢复原 image.ub；关闭跟踪不会改变运行内核。

initramfs 内临时改动及 /tmp 文件重启会丢失。导出结果到主机并核对摘要后再重启。测试部署不要覆盖唯一的基准镜像或用有文件系统警告的存储做写压力。

启动历史可回查 [baseline](board/baseline-first-boot-20261027.md)、[RT](board/rt-first-boot-20261027.md)及[原始串口日志](../logs/board/2026-10-27/)；它们是当期证据，当前状态以测试总结为准。
