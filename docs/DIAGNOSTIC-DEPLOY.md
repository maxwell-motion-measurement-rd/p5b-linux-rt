# 诊断镜像下载、部署与运行核验

本页用于复现 P5 XCZU4EV 已验证的独立 Linux 诊断环境。它启用 PREEMPT_RT、三核、ftrace 与 ARM PMU，包含匹配模块和诊断工具；不包含 Core3/AMP 通信实验所需的内存预留，不用于通信实验。

## 1. 下载与校验

从[诊断 Release](https://github.com/maxwell-motion-measurement-rd/p5b-linux-rt/releases/tag/diagnostic-ftrace-20261029)下载 `p5-ftrace-diagnostic-20261029.zip` 和同名 `.zip.sha256`。仅部署已有包无需启动 Ubuntu 虚拟机或重新编译；进行板端复测时才需要开发板、PS UART、SD 卡和读卡器。Release 为诊断用途预发布，不表示产品实时验收通过。

ZIP 为 40,856,302 字节，SHA-256：

```text
b70357452556328797f05b3b47215c0cf13220ee3509688918e812f830aa620a
```

Windows PowerShell 在下载目录手动运行：

```powershell
Get-FileHash .\p5-ftrace-diagnostic-20261029.zip -Algorithm SHA256
```

将输出与外部校验文件比较，完全一致后解压到新目录。Linux 可在 ZIP 和校验文件所在目录执行 `sha256sum -c p5-ftrace-diagnostic-20261029.zip.sha256`；解压后进入包根目录执行 `sha256sum -c SHA256SUMS` 核对包内文件。

| 包内路径 | 用途 |
| --- | --- |
| diagnostic/image.ub | 诊断内核、原三核 DTB、带匹配模块及诊断工具的 initramfs |
| original/image.ub | 恢复原始 RT 测量基准的镜像 |
| evidence/ | 配置与构建、模块、rootfs、FIT 校验证据 |
| source/ | 当期构建及采集脚本，属于历史版本 |
| SHA256SUMS | 包内文件校验清单 |

本包没有 BOOT.BIN 和 boot.scr。首次准备 SD 卡时，先按[原始 RT 部署指南](DEPLOY.md)从[原始启动 Release](https://github.com/maxwell-motion-measurement-rd/p5b-linux-rt/releases/tag/board-boot-20261027)取得匹配启动文件并完成 baseline／原始 RT 启动核验。不能把诊断 ZIP 本身当作整卡镜像烧写。

## 2. 部署前确认与替换

1. 核对实板 P5 XCZU4EV、载板与硬件设计；软件名称 P5B 不代表其他板型自动兼容。
2. 保存当前串口输出和 SD 启动文件。板端手动执行 `sync`、`poweroff`，确认关机完成后断电，再取卡。
3. 读卡器接入电脑，核对盘符。备份并校验启动分区根目录的 BOOT.BIN、boot.scr、image.ub。
4. 保留匹配且已验证的 BOOT.BIN 和 boot.scr，只用包内 `diagnostic/image.ub` 替换根目录的 `image.ub`。
5. 读回文件大小及 SHA-256，安全弹出。诊断 image.ub 为 21,510,740 字节，SHA-256 应为：
   
   ```text
   c81f2203d00dcc086fb0e42dc7e321b71f52be94bcf22f2254e37e474edbb943
   ```

6. 断电插回 SD 卡，保持已核对的 SD 启动拨码。连接 PS UART（115200、8N1、无流控），打开日志后上电；同一串口只由一个程序占用。

仅发布或下载附件不需要连接开发板。上述操作属于需要用户手动完成的实际部署流程。

## 3. 在开发板 Linux 核验

在串口终端手动执行：

```sh
uname -r
cat /sys/kernel/realtime
cat /sys/devices/system/cpu/online
ls /lib/modules
zcat /proc/config.gz | grep -E 'CONFIG_PREEMPT_RT=|CONFIG_FTRACE=|CONFIG_ARM_PMU='
ls /opt/rt-diagnostics
dmesg
```

预期内核版本为 `5.4.0-rt1-xilinx-v2020.2-p5b-diag-ftrace`，realtime 为 1，CPU online 为 0-2，模块目录与版本一致；配置启用 PREEMPT_RT、FTRACE、ARM_PMU。镜像内 `/opt/rt-diagnostics` 包含 perf、cyclictest、rtload 和旧采集脚本，工具不会自动运行。还须核对 tracefs 可用事件和 PMU 硬件事件实际有值，不能只看版本、配置或命令退出码。

## 4. 使用当前采集脚本

为了保留原始归档字节，本发布 ZIP 未重打包：

- README 的“尚未上板”是打包时状态。后续已完成启动、10 秒空载完整事件采集和 A53 PMU 验证，见[上板实测报告](../logs/rt-diagnostics/2026-10-29/board-trace/report.md)。
- 包内 `source/ftrace-short-capture.sh` 和镜像内同名脚本采用旧参数：每核 4MiB，未明确选择 mono。首次测试出现缓冲区覆盖。
- 实际完整复测使用每核 16MiB、mono 时钟。复现时使用[仓库当前采集脚本](../work/scripts/ftrace-short-capture.sh)，先阅读并核对参数，再通过自己的文件传输方式放到板端临时目录；不要直接运行镜像内旧脚本。
- 每轮使用新结果目录，保存命令、配置、镜像摘要、退出码、原始 trace 和各核缓冲区统计。检查 overrun、commit overrun、dropped events 后再解释事件；导出结果并校验后再关机，/tmp 随重启丢失。

测试参数与指标见[内核测试方法与结果](reports/rt-assessment-summary-20261029.md)。独立诊断镜像的 10 秒空载结果不能证明原始 RT 负载下 1255／1293µs 尖峰已修复，也不能替代产品实时验收。

## 5. 回退

板端正常关机、断电后取卡，将备份的原 image.ub 或包内 `original/image.ub` 恢复为启动分区根目录的 `image.ub`，读回校验、安全弹出后重新启动。原始 RT image.ub SHA-256：

```text
f7c224640ad30359a731a5492f06769b4f081496c88fbe273022c48fd2789484
```

关闭跟踪或退出 perf 不会把诊断内核变回原始 RT。需要修改配置或重建时，另见[源码重建说明](build/REPRODUCE.md#从原始流程生成诊断内核)。
