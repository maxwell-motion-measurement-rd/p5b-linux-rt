# AMP（非对称多处理，不同处理器核运行不同的软件系统） 验证版本：构建与手动加载

本页复现 2026-10-30 的 r001（本实验第1次修订的基础启动版本） 基础镜像＋r004（本实验第4次修订的通信驱动与裸机程序版本） RAM（运行内存，断电后其中的临时内容丢失） 最小通信实验。范围与结果见[阶段总览](../reports/amp-stage-summary-20261030.md)。用户已暂缓自动启动和持久化 r004，本页不安装开机服务。

## 固定版本与文件

| 内容 | 源码／入口 |
| --- | --- |
| 裸机（不依赖操作系统、直接在处理器上运行程序的方式） r004 | `amp/core3-g4/start-comm.S`、`ipc.c`、`link.ld` |
| Linux r004 驱动（Linux 侧管理硬件或通信接口的代码）与短测 | `amp/linux-g4/` |
| 公共编码与槽布局 | `amp/protocol/` |
| G5（编号为5的验证关卡，检查长测与重复启动） 正常通信、负载及重启测试 | `amp/linux-g5/` |
| r004 构建记录 | [amp-build-g4.sh](../../work/scripts/amp-build-g4.sh)、[最终构建输出](../../logs/amp/2026-10-30/g4/build-final-watchdog.txt) |
| G5 构建记录 | [amp-build-g5.sh](../../work/scripts/amp-build-g5.sh)、[构建摘要](../../logs/amp/2026-10-30/g5/build-final.txt) |

`amp/core3/`、`amp/linux-comm/` 保存早期 r001—r003（本实验第3次修订的通信程序版本） 实现，不要将这些目录误作 r004。r004 的状态页版本为 4，消息线格式版本为 1。

已验证镜像与载荷的手动加载快照见 [amp-comm-validation-20261030 Release](https://github.com/nozomiiiii/p5b-linux-rt/releases/tag/amp-comm-validation-20261030)，下载 `p5-amp-manual-r004-20261030.zip` 及校验文件。包内 `sd-base-r001/` 是原已验证基础三件套，`ram-r004/` 是临时载荷，`symbols-r004/` 保存裸机调试符号；不包含开机服务，不改变原镜像。先核对 ZIP 外部摘要，再核对包内 SHA256SUMS。

核对实际 P5 XCZU4EV 与配套硬件设计。r001 基础 FIT（把内核、设备树和内存根文件系统等载荷放在一起的启动镜像格式） 的 SHA-256（计算文件摘要的算法，用于核对文件内容是否一致） 为 `4723c5a96151f3b75c70a10705b5e9d5a80b14b7d2753cf8daa3d7c70cd1d2a0`，与[原始 RT 发布包](../../docs/DEPLOY.md)的 FIT 不同。原始 RT 包没有本实验所需的内存保留，不能直接加载 AMP 驱动。

基础 DT（设备树，描述硬件及资源配置） 必须包含[两个 2MiB no-map 区域](../../configs/p5b-amp-memory.dtsi)，Linux possible／online 均为 0—2。保持本实验启动参数 `cpuidle.off=1 clk_ignore_unused pd_ignore_unused`，不要与另一套 RT 测试条件混用。BOOT.BIN／boot.scr 和现有 SD 镜像备份仍按[部署指南](../DEPLOY.md)核对与保留。

## 构建输入

需要匹配 Linux `5.4.0-rt1-xilinx-v2020.2-p5b` 的原始 RT 源码、配置、Module.symvers 与独立实验内核输出目录，以及 Xilinx 2020.2 的 AArch64 Linux GCC9.2.0／sysroot 和裸机 AArch64 工具链。原始内核重建见[REPRODUCE](REPRODUCE.md)。

构建脚本保留原实验路径，以便对应日志；跨机器运行前修改脚本中的 `r`（独立实验根目录）、`b`（RT 源码根）、`p`（裸机前缀）、`recipe`／`lp`（Linux sysroot／编译器），以及模块 make 命令的独立 `O=` 输出目录。`M=` 编译外部模块前，须有同版本内核配置和符号文件；不在唯一的基准构建目录中执行清理。

把最终源码放入独立实验目录，保持相对 include 关系：

```sh
export AMP_ROOT="$HOME/p5-amp-r004-rebuild"
mkdir -p "$AMP_ROOT/core3" "$AMP_ROOT/linux-comm" "$AMP_ROOT/linux-g5" "$AMP_ROOT/protocol"
cp amp/core3-g4/* "$AMP_ROOT/core3/"
cp amp/linux-g4/* "$AMP_ROOT/linux-comm/"
cp amp/linux-g5/* "$AMP_ROOT/linux-g5/"
cp amp/protocol/* "$AMP_ROOT/protocol/"
# 修改并核对构建脚本路径后，在构建主机顺序执行：
bash work/scripts/amp-build-g4.sh
bash work/scripts/amp-build-g5.sh
```

`AMP_ROOT` 应与修改后的 `r` 一致，设为新建的实验目录。r004 构建输出包含固件（面向特定硬件、完成特定功能的底层程序）、ELF（可执行文件格式，可记录程序入口和内存布局）／map／反汇编、Linux 模块及 g3_test／g4_test；G5 输出包含 g5_test、g5_load、g5_snapshot、g5_recovery。G5 仅新增 Linux 用户态工具，不改变裸机固件或驱动。

已验证的固件 SHA-256 为 `df3e9d5c3befa9a84a6a2710a8f6e8d88461de839dbc83748496afe89751bf88`，模块为 `9449887e29a0003242ce8b5a49ddb65d62dce97067e4efe218d313bb33ef7ece`。重新构建应记录自己的输入与摘要，不能仅凭文件名认定与验证版本相同；ELF LOAD 范围、入口、页表／向量对齐和模块 vermagic 另行核对。

核对 ELF 可运行 `aarch64-none-elf-readelf -h -l build/core3-comm.elf`，入口应为 `0x60000000`，所有 LOAD／BSS／栈位于 `[0x60000000,0x60200000)`；原版本实际段结束为 `0x60008540`。向量须 2KiB 对齐、页表须 4KiB 对齐，以 [ELF 检查脚本](../../work/scripts/validate-amp-heartbeat.py)和反汇编检查。主机执行 `modinfo -F vermagic build/p5_core3_comm.ko`，应匹配 `5.4.0-rt1-xilinx-v2020.2-p5b` 及该内核的其余 vermagic 标志。工具前缀按实际安装路径替换。

## 板端手动启动

以下四个文件放到 `/tmp/amp-r004/`，前两项为运行载荷，后两项为验证工具；完整快照另含 G3（编号为3的验证关卡，检查双向消息正确性）／G4（编号为4的验证关卡，检查故障识别与恢复）／G5 恢复工具。

| 文件 | 用途 | 已验证 SHA-256 |
| --- | --- | --- |
| p5-core3-comm.bin | Core3（第4个 A53 处理器核） 固件 | df3e9d5c3befa9a84a6a2710a8f6e8d88461de839dbc83748496afe89751bf88 |
| p5_core3_comm.ko | Linux 驱动 | 9449887e29a0003242ce8b5a49ddb65d62dce97067e4efe218d313bb33ef7ece |
| g5_test | 正常双向通信测试 | 4e879ae7031aef10460bfd789385d50b6f2ce2e22ff94c25f46daf4ca6da6e31 |
| g5_snapshot | 状态与计数快照 | 74fa215440a4fa33a4e57d3bfc9205ea23d49dfcb4f43a2aa9b6bee7db2c0680 |

以下会实际启动 Core3，只能在匹配基础镜像完成冷启动、核对版本／内存预留之后操作。通过串口或可信文件传输把配套文件放到 `/tmp/amp-r004`，先检查 SHA-256。串口为 115200、8N1、无流控，同一时刻只由一个程序占用。

```sh
uname -r
cat /sys/devices/system/cpu/possible
cat /sys/devices/system/cpu/online
mkdir -p /lib/firmware
cp /tmp/amp-r004/p5-core3-comm.bin /lib/firmware/p5-core3-comm.bin
insmod /tmp/amp-r004/p5_core3_comm.ko
cat /sys/module/p5_core3_comm/parameters/fault_tests
cat /sys/bus/platform/devices/core3-heartbeat/status
```

加载驱动不会唤醒 Core3。确认 `fault_tests=N`、`attempted=0 pm_query=0 pm_state=0` 后，只执行一次：

```sh
printf 1 > /sys/bus/platform/devices/core3-heartbeat/start
sleep 2
cat /sys/bus/platform/devices/core3-heartbeat/status
cat /sys/bus/platform/devices/core3-heartbeat/stats
```

预期版本 4、core=3、el=12、state=1、reason=0，ESR／ELR／FAR 为 0，心跳（定期更新的存活标志）持续增长。异常时保留现场，不重试唤醒、不强制复位、不尝试卸载已启动 Core3 的模块。需要恢复时先同步并卸载存储，再正常关机及整板断电；本实验关机末段经常串口静默，不能将其写成已收到最终停机标记。

驱动设备 `/dev/p5-core3` 为 root 专用且独占打开。启动状态检查通过后，可在无其他通信客户端时执行正常短测：

```sh
chmod 755 /tmp/amp-r004/g5_test /tmp/amp-r004/g5_snapshot
/tmp/amp-r004/g5_snapshot
/tmp/amp-r004/g5_test forward 100 &&
/tmp/amp-r004/g5_test reverse 100 &&
/tmp/amp-r004/g5_test cross 100
/tmp/amp-r004/g5_snapshot
```

三个模式都应输出 `passed=100`、`errors=0`、`missed_release=0`。一次全新启动前后每方向计数应由 0 增至 503，错误／超时（规定时间内没有等到预期结果）／失联保持 0，双方心跳增长。已有计数时比较增量，不要求清零或热重启。

G4 故障与 G5 恢复程序需要在启动前以 `fault_tests=1` 加载模块，并会主动暂停、拒收或重置通信。不要在已接入业务的实例上直接运行故障脚本。

## 离线核对已有证据

```sh
python work/scripts/analyze-amp-g3.py logs/amp/2026-10-30/g3
python work/scripts/analyze-amp-g4.py
python work/scripts/analyze-amp-g5.py logs/amp/2026-10-30/g5/amp-g5-evidence.tar.gz
python work/scripts/analyze-amp-g5-cold.py
```

分析脚本检查日志、摘要和结果，不运行板端测试。G5 压力结果与冷启动结果分别输出；[G5 汇总](../../logs/amp/2026-10-30/g5/results.json)记录最终验收范围与第五次早期启动日志缺口。仓库保留校验过的规范数据，重复传输文本和轮询（程序反复检查是否有新消息）快照已按[清理记录](../reports/amp-cleanup-20261030.md)删除。
