# AMP（Asymmetric Multiprocessing，非对称多处理，不同处理器核运行不同的软件系统） 验证版本：构建与手动加载

本页复现 2026-10-30 的 r001（本实验第1次修订的基础启动版本） 基础镜像＋r004（本实验第4次修订的通信驱动与裸机程序版本） RAM 最小通信实验。范围与结果见[阶段总览](../reports/amp-stage-summary-20261030.md)。用户已暂缓自动启动和持久化 r004，本页不安装开机服务。

## 固定版本与文件

| 内容 | 源码／入口 |
| --- | --- |
| 裸机 r004 | `amp/core3-g4/start-comm.S`、`ipc.c`、`link.ld` |
| Linux r004 驱动与短测 | `amp/linux-g4/` |
| 公共编码与槽布局 | `amp/protocol/` |
| G5（检查长测与重复启动） 正常通信、负载及重启测试 | `amp/linux-g5/` |
| r004 构建记录 | [amp-build-g4.sh](../../work/scripts/amp-build-g4.sh)、[最终构建输出](../../logs/amp/2026-10-30/g4/build-final-watchdog.txt) |
| G5 构建记录 | [amp-build-g5.sh](../../work/scripts/amp-build-g5.sh)、[构建摘要](../../logs/amp/2026-10-30/g5/build-final.txt) |

`amp/core3/`、`amp/linux-comm/` 保存早期 r001—r003（本实验第3次修订的通信程序版本） 实现，不要将这些目录误作 r004。r004 的状态页版本为 4，消息线格式版本为 1。

已验证镜像与载荷的手动加载快照见 [amp-comm-validation-20261030 Release](https://github.com/maxwell-motion-measurement-rd/p5b-linux-rt/releases/tag/amp-comm-validation-20261030)，下载 `p5-amp-manual-r004-20261030.zip` 及校验文件。包内 `sd-base-r001/` 是原已验证基础三件套，`ram-r004/` 是临时载荷，`symbols-r004/` 保存裸机调试符号；不包含开机服务，不改变原镜像。先核对 ZIP 外部摘要，再核对包内 SHA256SUMS。

核对实际 P5 XCZU4EV 与配套硬件设计。r001 基础 FIT（Flattened Image Tree，把内核、设备树等载荷组织在一起的启动镜像格式） 的 SHA-256（计算文件摘要的算法，用于核对文件内容是否一致） 为 `4723c5a96151f3b75c70a10705b5e9d5a80b14b7d2753cf8daa3d7c70cd1d2a0`，与[原始 RT 发布包](../../docs/DEPLOY.md)的 FIT 不同。原始 RT 包没有本实验所需的内存保留，不能直接加载 AMP 驱动。

基础 DT（Device Tree，设备树，描述硬件及资源配置） 必须包含[两个 2MiB no-map 区域](../../configs/p5b-amp-memory.dtsi)，Linux possible／online 均为 0—2。保持本实验启动参数 `cpuidle.off=1 clk_ignore_unused pd_ignore_unused`，不要与另一套 RT 测试条件混用。BOOT.BIN／boot.scr 和现有 SD 镜像备份仍按[部署指南](../DEPLOY.md)核对与保留。

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

`AMP_ROOT` 应与修改后的 `r` 一致，设为新建的实验目录。r004 构建输出包含固件、ELF（Executable and Linkable Format，可执行与可链接格式，可记录程序入口和内存布局）／map／反汇编、Linux 模块及 g3_test／g4_test；G5 输出包含 g5_test、g5_load、g5_snapshot、g5_recovery。G5 仅新增 Linux 用户态工具，不改变裸机固件或驱动。

已验证的固件 SHA-256 为 `df3e9d5c3befa9a84a6a2710a8f6e8d88461de839dbc83748496afe89751bf88`，模块为 `9449887e29a0003242ce8b5a49ddb65d62dce97067e4efe218d313bb33ef7ece`。重新构建应记录自己的输入与摘要，不能仅凭文件名认定与验证版本相同；ELF LOAD 范围、入口、页表／向量对齐和模块 vermagic 另行核对。

核对 ELF 可运行 `aarch64-none-elf-readelf -h -l build/core3-comm.elf`，入口应为 `0x60000000`，所有 LOAD／BSS／栈位于 `[0x60000000,0x60200000)`；原版本实际段结束为 `0x60008540`。向量须 2KiB 对齐、页表须 4KiB 对齐，以 [ELF 检查脚本](../../work/scripts/validate-amp-heartbeat.py)和反汇编检查。主机执行 `modinfo -F vermagic build/p5_core3_comm.ko`，应匹配 `5.4.0-rt1-xilinx-v2020.2-p5b` 及该内核的其余 vermagic 标志。工具前缀按实际安装路径替换。

## 板端手动启动

先理解原理可读[通信原理与验证解读](../AMP-COMMUNICATION-EXPLAINED.md)：区分文件上传、驱动加载、Core3启动和消息会话建立，并用三种模式的时序说明每方向503帧的来源。下面按步骤操作，验证标准与该文对应。

以下四个文件放到 `/tmp/amp-r004/`，前两项为运行载荷，后两项为验证工具；完整快照另含 G3（检查双向消息正确性）／G4（检查故障识别与恢复）／G5 恢复工具。

| 文件 | 用途 | 已验证 SHA-256 |
| --- | --- | --- |
| p5-core3-comm.bin | Core3 固件 | df3e9d5c3befa9a84a6a2710a8f6e8d88461de839dbc83748496afe89751bf88 |
| p5_core3_comm.ko | Linux 驱动 | 9449887e29a0003242ce8b5a49ddb65d62dce97067e4efe218d313bb33ef7ece |
| g5_test | 正常双向通信测试 | 4e879ae7031aef10460bfd789385d50b6f2ce2e22ff94c25f46daf4ca6da6e31 |
| g5_snapshot | 状态与计数快照 | 74fa215440a4fa33a4e57d3bfc9205ea23d49dfcb4f43a2aa9b6bee7db2c0680 |

### 1. 从Windows通过串口传输文件

本节用于已经从`sd-base-r001/`冷启动Linux、准备重放Release的情况，无需执行上面的“构建输入”。顺序为：**传输文件 → 核对摘要 → 核对启动环境 → 加载驱动并检查状态 → 单次启动Core3 → 通信短测**。每一步通过后再执行下一步；不要一次粘贴整页命令。

这里的`ram-r004/`是电脑上解压后的目录，`/tmp/amp-r004/`是板端Linux目录。以下串口上传方式曾用于原实验，本次手动复现也已完成四个文件传输并核对摘要；它通过板端shell分块写文件，不需要网络或额外串口文件传输协议。

准备：

1. 在Windows电脑上准备本仓库副本和已校验的Release解压目录。上传脚本位于仓库的`work/scripts/`，不在Release的`ram-r004/`内。
2. 用串口终端连接板子（115200、8N1、无流控），确认已进入`root@ALIENTEK-MP:~#`命令行；若仍在登录提示，先登录root。
3. 断开串口终端的连接，保持板子供电及Linux运行，让上传脚本独占串口。传输完成后再连接终端。
4. 在**电脑的Windows PowerShell**中查询串口：

```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
Get-CimInstance Win32_SerialPort | Select-Object DeviceID, Name
```

当前[固件／驱动上传脚本](../../work/scripts/amp-serial-upload-r004.ps1)和[G5工具上传脚本](../../work/scripts/amp-serial-upload-g5.ps1)均固定使用`COM3`。确认系统实际列出COM3后再执行；若使用其他端口，先将两份脚本中`SerialPort`构造处的`'COM3'`改为实际串口号。出现“端口COM3不存在”时，先检查系统识别的端口、USB串口连接和驱动，不要继续上传；“访问被拒绝”时检查是否仍有其他程序占用串口。此前这次COM3故障的具体原因未记录，不据此断言是哪一种原因。

在同一Windows PowerShell窗口执行下列完整代码块。`$repo`改为电脑上的仓库路径，`$payload`改为解压后的`ram-r004`路径；以下路径为本次复现示例。外层`& { ... }`确保上传报错后停止后续文件传输。

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'C:\Users\13931\Documents\ChatGPT\maxwell_implementation_dual axis drive and control'
    $payload = 'C:\Users\13931\Desktop\linux_rt_setup\p5-amp-manual-r004-20261030\ram-r004'
    $logs = Join-Path $env:TEMP ('amp-upload-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    $names = @('p5-core3-comm.bin', 'p5_core3_comm.ko', 'g5_test', 'g5_snapshot')
    foreach ($name in $names) {
        if (-not (Test-Path -LiteralPath (Join-Path $payload $name) -PathType Leaf)) {
            throw "本地文件不存在：$name"
        }
    }
    foreach ($script in @('amp-serial-upload-r004.ps1', 'amp-serial-upload-g5.ps1')) {
        if (-not (Test-Path -LiteralPath "$repo\work\scripts\$script" -PathType Leaf)) {
            throw "上传脚本不存在：$script，请检查仓库路径"
        }
    }
    if ([System.IO.Ports.SerialPort]::GetPortNames() -notcontains 'COM3') {
        throw '系统未列出COM3，请先核对串口；其他端口须同时修改两份脚本和此检查'
    }
    New-Item -ItemType Directory -Path $logs | Out-Null
    Write-Output "上传日志目录：$logs"
    foreach ($name in $names) {
        $script = if ($name -in @('p5-core3-comm.bin', 'p5_core3_comm.ko')) {
            'amp-serial-upload-r004.ps1'
        } else {
            'amp-serial-upload-g5.ps1'
        }
        & "$repo\work\scripts\$script" -LocalFile (Join-Path $payload $name) -RemoteName $name -LogPath (Join-Path $logs "upload-$name.txt")
        if (-not $?) { throw "上传失败：$name，请检查日志" }
    }
    Write-Output '四个文件上传流程结束；重新连接串口终端，在板端核对摘要。'
}
```

预期每个文件都有`Uploaded ...`完成提示。脚本在板端先写`.part`临时文件，再改为正式文件名并输出SHA-256到日志；仍须按下一步核对摘要。打印日志目录、命令提示符重新出现，都不代表传输成功。遇到报错立即停止，保存输出和日志；若PowerShell提示禁止运行脚本，先记录完整报错，当前操作尚未开始传输。本段整理后的批量命令已做语法检查，尚待首次使用者按新版文字完整重放；原上传脚本和四个载荷字节未修改。

### 2. 在板端确认文件与摘要

重新连接串口终端，在**板端Linux的root命令行**执行：

```sh
ls -l /tmp/amp-r004/
sha256sum /tmp/amp-r004/p5-core3-comm.bin \
          /tmp/amp-r004/p5_core3_comm.ko \
          /tmp/amp-r004/g5_test \
          /tmp/amp-r004/g5_snapshot
```

四个文件的摘要必须逐项与上表相同；缺文件、出现读取错误或摘要不一致时，不加载驱动，先查传输问题。文件传到板端不代表驱动已加载或Core3已启动。`g5_test`和`g5_snapshot`此时没有执行权限是正常的，通信短测前会设置权限。保留本次上传日志和摘要输出。

### 3. 在板端核对启动环境（只读）

保持板端root命令行，先执行这一块，核对通过后再进入第4步：

```sh
uname -r
cat /sys/devices/system/cpu/possible
cat /sys/devices/system/cpu/online
cat /proc/cmdline
ls /proc/device-tree/reserved-memory/
od -An -v -tx1 /proc/device-tree/reserved-memory/core3-private@60000000/reg
od -An -v -tx1 /proc/device-tree/reserved-memory/core3-shared@60200000/reg
for node in core3-private@60000000 core3-shared@60200000; do
    if test -e "/proc/device-tree/reserved-memory/$node/no-map"; then
        echo "$node: no-map present"
    else
        echo "$node: ERROR no-map missing"
    fi
done
```

| 检查项 | 预期结果 |
| --- | --- |
| `uname -r` | `5.4.0-rt1-xilinx-v2020.2-p5b` |
| `possible`、`online` | 两项均为`0-2` |
| `/proc/cmdline` | 包含`cpuidle.off=1`、`clk_ignore_unused`、`pd_ignore_unused`，其他参数按实际完整记录 |
| 私有区`reg`字节 | `00 00 00 00 60 00 00 00 00 00 00 00 00 20 00 00` |
| 共享区`reg`字节 | `00 00 00 00 60 20 00 00 00 00 00 00 00 20 00 00` |
| `no-map` | 两个节点均输出`no-map present` |

`reg`以大端字节显示：两行分别表示起始地址`0x60000000`／`0x60200000`，大小均为`0x00200000`（2MiB）。`no-map`是空属性，检查的是属性存在，不要求有文本内容。只列出节点名称不足以证明地址和`no-map`正确。上述条件任一不符或命令报错时停止，不执行`insmod`；保存输出并核对SD启动文件与基础镜像。此处补齐了原正文要求但原代码块缺少的检查，新增命令的本次板端输出尚未收集。

### 4. 复制固件、加载驱动并检查启动前状态

仅在第2、3步通过、当前冷启动尚未加载通信模块时，在**板端Linux**执行。`cp`将固件放到驱动读取的位置，`insmod`加载Linux驱动；二者不会启动Core3。链式命令保证前一步失败时不继续后面的操作。

```sh
mkdir -p /lib/firmware &&
cp /tmp/amp-r004/p5-core3-comm.bin /lib/firmware/p5-core3-comm.bin &&
insmod /tmp/amp-r004/p5_core3_comm.ko &&
cat /sys/module/p5_core3_comm/parameters/fault_tests &&
cat /sys/bus/platform/devices/core3-heartbeat/status
```

`mkdir`、`cp`和`insmod`成功通常没有额外输出，随后应看到`fault_tests`为`N`，状态包含`attempted=0 pm_query=0 pm_state=0`。这一步尚不要求Core3心跳增长。模块加载报错、状态文件缺失、模块已经加载或状态与预期不符时停止并保存输出，不重复`insmod`，不直接进入启动命令。

### 5. 单次启动Core3

加载驱动不会唤醒 Core3。确认 `fault_tests=N`、`attempted=0 pm_query=0 pm_state=0` 后，只执行一次：

```sh
printf 1 > /sys/bus/platform/devices/core3-heartbeat/start
sleep 2
cat /sys/bus/platform/devices/core3-heartbeat/status
cat /sys/bus/platform/devices/core3-heartbeat/stats
```

预期版本 4、core=3、el=12、state=1、reason=0，ESR／ELR／FAR 为 0，心跳持续增长。异常时保留现场，不重试唤醒、不强制复位、不尝试卸载已启动 Core3 的模块。需要恢复时先同步并卸载存储，再正常关机及整板断电；本实验关机末段经常串口静默，不能将其写成已收到最终停机标记。

### 6. 正常通信短测

驱动设备 `/dev/p5-core3` 为 root 专用且独占打开。启动状态检查通过后，可在无其他通信客户端时执行正常短测：

```sh
chmod 755 /tmp/amp-r004/g5_test /tmp/amp-r004/g5_snapshot
/tmp/amp-r004/g5_snapshot
/tmp/amp-r004/g5_test forward 100 &&
/tmp/amp-r004/g5_test reverse 100 &&
/tmp/amp-r004/g5_test cross 100
/tmp/amp-r004/g5_snapshot
```

三个模式都应输出 `passed=100`、`errors=0`、`missed_release=0`。一次全新启动前后每方向计数应由 0 增至 503，错误／超时／失联保持 0，双方心跳增长。已有计数时比较增量，不要求清零或热重启。

G4 故障与 G5 恢复程序需要在启动前以 `fault_tests=1` 加载模块，并会主动暂停、拒收或重置通信。不要在已接入业务的实例上直接运行故障脚本。

## 离线核对已有证据

以下分析器会写入或更新结构化结果文件，并非全部只读。请在独立的仓库副本中执行，保留原证据与原汇总不变；将本次输出与已归档结果比较，不直接在唯一的证据目录中重跑。

```sh
python work/scripts/analyze-amp-g3.py logs/amp/2026-10-30/g3
python work/scripts/analyze-amp-g4.py
python work/scripts/analyze-amp-g5.py logs/amp/2026-10-30/g5/amp-g5-evidence.tar.gz
python work/scripts/analyze-amp-g5-cold.py
```

分析脚本检查日志、摘要和结果，不运行板端测试。G5 压力结果与冷启动结果分别输出；[G5 汇总](../../logs/amp/2026-10-30/g5/results.json)记录最终验收范围与第五次早期启动日志缺口。仓库保留校验过的规范数据，重复传输文本和轮询快照已按[清理记录](../reports/amp-cleanup-20261030.md)删除。
