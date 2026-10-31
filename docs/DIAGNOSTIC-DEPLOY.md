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

## 4. 手动运行测试

第 3 节只核验环境，不会自动开始测试。本节命令均由读者手动执行，不需要 Ubuntu 虚拟机或重新编译。除导出步骤明确标注 Windows PowerShell 外，全部在**开发板 Linux 的串口终端中，以 root 身份执行**。各代码块按顺序、在同一个 Shell 会话中运行。先开启串口软件的会话日志，记录本次主机日期及部署镜像摘要；不同时运行旧测试、perf 和 ftrace。

### 4.1 准备工具和独立结果目录

```sh
id -u
ls -l /opt/rt-diagnostics/cyclictest /opt/rt-diagnostics/perf /opt/rt-diagnostics/rtload
command -v mktemp tar gzip base64 sha256sum
```

预期用户编号 0，三个工具有执行权限，后续所需命令均可用。缺文件、权限不符或第 3 节版本核验未通过时停止，先排查。

下面整块复制到板端执行，设置路径、保存现场并定义日志函数：

```sh
TOOLS=/opt/rt-diagnostics
OUT=$(mktemp -d /tmp/rt-test.XXXXXX)
echo "本轮结果目录：$OUT"

run_logged() {
    label=$1
    shift
    if [ -e "$OUT/$label.txt" ]; then
        echo "结果文件已存在，停止以避免覆盖"
        return 2
    fi
    "$@" > "$OUT/$label.txt" 2>&1
    result=$?
    printf '%s\n' "$result" > "$OUT/$label.exit"
    cat "$OUT/$label.txt"
    echo "退出码=$result"
    return "$result"
}

uname -a > "$OUT/uname.txt"
cat /sys/kernel/realtime > "$OUT/realtime.txt"
cat /sys/devices/system/cpu/online > "$OUT/cpu-online.txt"
zcat /proc/config.gz > "$OUT/kernel.config"
sha256sum "$TOOLS/cyclictest" "$TOOLS/perf" "$TOOLS/rtload" > "$OUT/tool-sha256.txt"
dmesg > "$OUT/dmesg-before.txt"
cat /proc/mounts > "$OUT/mounts.txt"
cat /proc/sys/kernel/sched_rt_period_us /proc/sys/kernel/sched_rt_runtime_us > "$OUT/rt-budget.txt"
for cpu in 0 1 2; do
    echo "CPU$cpu"
    for name in scaling_governor scaling_cur_freq; do
        file="/sys/devices/system/cpu/cpu$cpu/cpufreq/$name"
        if [ -r "$file" ]; then
            echo "$name=$(cat "$file")"
        fi
    done
done > "$OUT/cpu-frequency.txt"
```

记下 OUT 的实际路径。板端时钟可能不准，因此目录名使用随机唯一后缀。run_logged 将完整输出保存为 .txt、退出码保存为 .exit，并在结束后显示结果。出现非零退出码、初始化错误时停止后续测试，保留日志。换终端后变量和函数不会自动保留；重启后 /tmp 文件丢失。

### 4.2 cyclictest：5 秒工具自检

```sh
run_logged cyclictest-check "$TOOLS/cyclictest" --laptop -a1 -t1 -p80 --policy=fifo -m -i1000 -D5 -q -h2000
```

约 5 秒结束。-a1 绑定 CPU1，-t1 为一个测量线程，-p80 与 --policy=fifo 设置 FIFO 优先级 80，-m 锁定内存，-i1000 设置 1000µs 周期，-h2000 保存 2000µs 范围的直方图。--laptop 在此版本用于跳过 cpu_dma_latency 写入。

预期退出码 0、约 5000 个样本，检查 Min／Avg／Max 和 Histogram Overflows。溢出应为 0；有初始化、调度权限或锁内存错误时，不进入长测。延迟数值无需恰好等于历史记录。

### 4.3 cyclictest：10 分钟空载冒烟测试

自检正常后执行：

```sh
run_logged cyclictest-idle "$TOOLS/cyclictest" --laptop -a1 -t1 -p80 --policy=fifo -m -i1000 -D10m -q -h2000
```

运行约 10 分钟。-q 和输出重定向使运行中没有持续输出，这是正常现象，不要重复启动。期间不额外运行 CPU／内存压力、perf 或 ftrace。

预期退出码 0、约 600000 个样本。保存直方图、溢出数及 Min／Avg／Max；存在溢出时不能只评价桶内分位数。当前诊断内核与原始 RT 配置不同，结果单独记录，不能直接声称改善或修复了历史尖峰。

### 4.4 perf stat：软件事件与 A53 硬件计数

先进行约 10 秒软件事件统计：

```sh
run_logged perf-software "$TOOLS/perf" stat -e task-clock,context-switches,cpu-migrations,page-faults -- "$TOOLS/rtload" cpu 2 10
```

rtload cpu 2 10 表示在 CPU2 上，以普通 SCHED_OTHER 策略运行约 10 秒整数运算。预期 perf 退出码 0，各软件事件有数值；实际总时长包含准备和收尾，不必恰好 10.000 秒。

再检查硬件事件，此时仍未启用 ftrace：

```sh
run_logged perf-hardware "$TOOLS/perf" stat -e task-clock,cycles,instructions,cache-misses,branch-misses -- "$TOOLS/rtload" cpu 2 10
```

cycles、instructions、cache-misses、branch-misses 应有实际数值。如果显示 <not supported> 或 <not counted>，即使退出码 0，也不能认定该事件验证通过；保存输出并检查 ARM_PMU 配置、驱动及权限。事件运行比例 100% 不是 CPU 利用率或性能得分。

本节 perf 与前面的 cyclictest 顺序执行，不是同一尖峰的联合采集，也不是 CPU 压力下的 cyclictest 测试。

### 4.5 perf record／report：10 秒软件事件采样

```sh
run_logged perf-record "$TOOLS/perf" record -e cpu-clock:u -F 99 -g --call-graph fp -o "$OUT/perf.data" -- "$TOOLS/rtload" cpu 2 10
```

预期退出码 0，生成非空 perf.data。然后解析同一文件：

```sh
ls -l "$OUT/perf.data"
run_logged perf-report "$TOOLS/perf" report --stdio --no-children -i "$OUT/perf.data"
```

99Hz、10 秒预期约千个样本，实际数目不必恰好 990。检查丢失样本、主要样本分布及解析错误。精简 perf 未启用 libelf／DWARF／libunwind，可能只能显示地址或 rtload 偏移，无法完整解析函数名；这是已记录的符号能力限制。保留 perf.data 与工具摘要，以便后续用匹配二进制分析。

### 4.6 ftrace：通过串口准备当前采集脚本

发布 ZIP 保留原始归档：README 的“尚未上板”是历史状态，后续已完成[上板验证](../logs/rt-diagnostics/2026-10-29/board-trace/report.md)。包内和镜像内旧脚本使用每核 4MiB，未明确选择 mono，首次采集发生覆盖。不要直接运行 /opt/rt-diagnostics/ftrace-short-capture.sh。

下面嵌入[当前仓库脚本](../work/scripts/ftrace-short-capture.sh)的固定副本，供只有串口、没有板端网络的同事使用。先检查是否有上轮实例或结果：

```sh
ls -ld /sys/kernel/tracing/instances/rt-audit /tmp/rt-ftrace-short /tmp/ftrace-short-capture.sh
```

首次运行这些路径不存在，ls 提示不存在是正常的；如果已存在，先停止本节并按第 5 节保存旧结果，不要为了重跑直接删除证据。未挂载 tracefs 时，此处也可能看不到已有实例，脚本挂载后还会再次检查。

确认首次运行后，将下面整块粘贴到板端终端。单独一行 P5_FTRACE_SCRIPT 是输入结束标记。期间终端出现 > 提示表示仍在接收文本，不要把 > 复制进脚本：

```sh
cat > /tmp/ftrace-short-capture.sh <<'P5_FTRACE_SCRIPT'
#!/bin/sh
# Run only after booting and verifying the separate diagnostic image.
set -eu
case "$(uname -r)" in *-diag-ftrace) ;; *) echo 'Diagnostic kernel required'; exit 2;; esac
test "$(cat /sys/kernel/realtime)" = 1
test "$(cat /sys/devices/system/cpu/online)" = 0-2
mkdir -p /tmp/rt-audit-tools
for tool in cyclictest rtload perf; do
    test -x "/tmp/rt-audit-tools/$tool" || cp "/opt/rt-diagnostics/$tool" "/tmp/rt-audit-tools/$tool"
done
trace=/sys/kernel/tracing
grep -q " $trace tracefs " /proc/mounts || mount -t tracefs nodev "$trace"
instance="$trace/instances/rt-audit"
test ! -e "$instance" || { echo 'Existing instance: export it before retry'; exit 2; }
mkdir "$instance"
out=/tmp/rt-ftrace-short
mkdir "$out"
cleanup() {
    echo 0 > "$instance/tracing_on"
    echo 0 > "$instance/events/enable"
}
trap cleanup EXIT INT TERM
echo 0 > "$instance/tracing_on"
echo nop > "$instance/current_tracer"
echo 7 > "$instance/tracing_cpumask"
echo 16384 > "$instance/buffer_size_kb"
echo mono > "$instance/trace_clock"
for event in sched/sched_waking sched/sched_wakeup sched/sched_switch irq/irq_handler_entry irq/irq_handler_exit irq/softirq_entry irq/softirq_exit; do
    test -f "$instance/events/$event/enable"
    echo 1 > "$instance/events/$event/enable"
done
cat "$instance/trace_clock" > "$out/trace_clock.txt"
echo > "$instance/trace"
echo 1 > "$instance/tracing_on"
/tmp/rt-audit-tools/cyclictest --laptop -a1 -t1 -p80 --policy=fifo -m -i1000 -D10 -q -h2000 > "$out/cyclictest.txt" 2>&1
echo 0 > "$instance/tracing_on"
cat "$instance/trace" > "$out/trace.txt"
for cpu in 0 1 2; do
    echo "CPU$cpu" >> "$out/buffer-stats.txt"
    cat "$instance/per_cpu/cpu$cpu/stats" >> "$out/buffer-stats.txt"
done
cleanup
gzip -c "$out/trace.txt" > "$out/trace.txt.gz"
sha256sum "$out"/*
echo 'Initial 10s idle capture only; inspect overrun and dropped events before interpretation.'
P5_FTRACE_SCRIPT
sha256sum /tmp/ftrace-short-capture.sh
```

上面只写入脚本，尚未运行。SHA-256 应为：

```text
6cddfb6e2eb706e06ba6453083db866e5a4883a561bb1577872d568978256b6b
```

摘要不一致说明可能粘贴丢字节，先停止，不执行。若自行采用更新版本的仓库脚本，使用对应版本摘要，并核对每核 16384KiB（16MiB）和 mono 参数；不要把旧参数脚本当作完整复测版本。

摘要一致后执行：

```sh
sh /tmp/ftrace-short-capture.sh > "$OUT/ftrace-run.txt" 2>&1
result=$?
printf '%s\n' "$result" > "$OUT/ftrace-run.exit"
cat "$OUT/ftrace-run.txt"
echo "退出码=$result"
```

采集约 10 秒，结束后导出 trace 还需要一些时间。脚本挂载 tracefs、创建独立实例、准备工具，自己运行 cyclictest 并记录 CPU0—2 的调度／中断事件。不要再同时启动第二个 cyclictest、perf 或压力程序。

### 4.7 ftrace：检查完整性和收尾

仅在采集退出码为 0、结果齐全时继续：

```sh
cat /tmp/rt-ftrace-short/trace_clock.txt
cat /tmp/rt-ftrace-short/cyclictest.txt
cat /tmp/rt-ftrace-short/buffer-stats.txt
cat /sys/kernel/tracing/instances/rt-audit/tracing_on
cat /sys/kernel/tracing/instances/rt-audit/events/enable
```

预期时钟输出中的 [mono] 表示当前时钟；各核 overrun、commit overrun、dropped events 均为 0；实例 tracing_on 和 events/enable 均为 0。cyclictest 约 10000 个样本。有覆盖／丢弃或缺文件时，保留失败记录，不能声称完整记录了整个 10 秒，也不能用缺失事件推断任务未执行。

确认跟踪已停止后，把结果复制到本轮目录并检查系统状态：

```sh
cp -R /tmp/rt-ftrace-short "$OUT/ftrace"
cp /tmp/ftrace-short-capture.sh "$OUT/ftrace-short-capture.sh"
dmesg > "$OUT/dmesg-after.txt"
diff -u "$OUT/dmesg-before.txt" "$OUT/dmesg-after.txt" > "$OUT/dmesg-diff.txt"
cat "$OUT/dmesg-diff.txt"
ps | grep -E '[c]yclictest|[r]tload|[p]erf'
```

diff 无输出表示两次日志一致；有差异时逐项判断。ps 用于检查本轮测试残留进程；发现仍在运行的测试时先保存状态并处理，不直接关机。没有新增内核日志不等于排除了所有竞争或稳定性问题。

### 4.8 本轮完成与失败判断

| 步骤 | 必须保存的输出 | 判断与停止条件 |
| --- | --- | --- |
| 环境与自检 | 版本、配置、CPU、工具摘要、5 秒输出与退出码 | 环境不符或工具初始化失败时停止 |
| 空载 cyclictest | 10 分钟直方图、样本数、Min／Avg／Max、溢出数 | 有溢出时不能只用桶内分位数评价尾部 |
| perf stat | 软件与硬件两组计数及退出码 | 事件有实际值才确认可用，不只看退出码 |
| perf record／report | perf.data、采样与解析输出、退出码 | 保留丢失样本信息；地址显示不直接等于采样失败 |
| ftrace | trace、时钟、各核缓冲区统计、cyclictest、脚本 | 覆盖／丢弃计数非零时不认定完整窗口可用 |
| 导出 | 归档字节数、SHA-256、主机读回结果 | 摘要不一致时不接受该导出包 |

以上覆盖诊断环境的工具验证及空载测量，不自动覆盖历史 CPU／内存并发压力场景。需要重放压力时，另按[原测量场景和编号命令](../logs/rt-risk/2026-10-29/103809-tools/)核对负载覆盖测量窗口，记录这是诊断内核的新结果。10 秒空载未出现尖峰不能证明原始 RT 的 1255／1293µs 问题已修复。

## 5. 导出结果：只有串口也能完成

### 5.1 在开发板打包并记录摘要

确认采集已停止，OUT 仍指向本轮目录：

```sh
echo "$OUT"
ls "$OUT"
ARCHIVE="$OUT.tar.gz"
tar -czf "$ARCHIVE" -C /tmp "$(basename "$OUT")"
ls -l "$ARCHIVE"
sha256sum "$ARCHIVE"
```

归档在结果目录外，避免递归打包自身。记下字节数和 SHA-256。/tmp 会随重启丢失，先导出再关机。

### 5.2 将归档输出到串口日志

保持串口软件正在保存会话日志，整块执行：

```sh
printf '\nRT_EVIDENCE_BEGIN\n'
base64 "$ARCHIVE"
printf '\nRT_EVIDENCE_END\n'
```

等待单独一行 RT_EVIDENCE_END 出现，再停止日志并保存到电脑，例如 C:\Users\13931\Desktop\rt-session.log。输出可能持续几分钟，期间不运行其他命令或测试。Base64 将二进制转为串口可保存的文本，不替代摘要校验；截断或丢字符的日志不能接受。

### 5.3 在电脑 Windows PowerShell 还原和校验

以下在**Windows PowerShell**执行，不是在开发板。修改日志路径和输出文件名，避免覆盖上一轮：

```powershell
$sessionLog = 'C:\Users\13931\Desktop\rt-session.log'
$exportPath = 'C:\Users\13931\Desktop\rt-evidence.tar.gz'
if (Test-Path -LiteralPath $exportPath) {
    throw '输出已存在，请换一个新文件名'
}
$logText = Get-Content -LiteralPath $sessionLog -Raw
$blocks = [regex]::Matches($logText, '(?ms)^RT_EVIDENCE_BEGIN\r?\n(?<data>.*?)^RT_EVIDENCE_END\r?$')
if ($blocks.Count -ne 1) {
    throw '应恰有一组导出标记，请确认日志完整且只导出一次'
}
$base64Text = $blocks[0].Groups['data'].Value -replace '\s', ''
$archiveBytes = [Convert]::FromBase64String($base64Text)
[IO.File]::WriteAllBytes($exportPath, $archiveBytes)
Get-Item -LiteralPath $exportPath | Select-Object Name, Length
Get-FileHash -LiteralPath $exportPath -Algorithm SHA256
```

主机字节数与 SHA-256 必须和板端记录完全一致。解码错误或摘要不符时，保留失败日志，重新导出到新的主机文件，不用损坏包分析。成功后用 7-Zip 等解压，核对本轮 .txt、.exit、perf.data 及 ftrace 文件存在。

如果已有可用且经确认的 SSH 网络连接，也可用 scp 传同一个归档；本流程不依赖网络。任何传输方式都要读回校验。

### 5.4 移除独立实例并正常关机

主机导出校验成功、且确认无残留测试进程后，在开发板执行：

```sh
echo 0 > /sys/kernel/tracing/instances/rt-audit/tracing_on
echo 0 > /sys/kernel/tracing/instances/rt-audit/events/enable
rmdir /sys/kernel/tracing/instances/rt-audit
sync
poweroff
```

这些路径适用于本节成功创建 rt-audit 的情况；前序失败或路径不存在时，先保存错误输出，不盲目继续。确认关机完成后再断电；板端临时结果不会保留到下次启动。

## 6. 回退

板端正常关机、断电后取卡，将备份的原 image.ub 或包内 `original/image.ub` 恢复为启动分区根目录的 `image.ub`，读回校验、安全弹出后重新启动。原始 RT image.ub SHA-256：

```text
f7c224640ad30359a731a5492f06769b4f081496c88fbe273022c48fd2789484
```

关闭跟踪或退出 perf 不会把诊断内核变回原始 RT。需要修改配置或重建时，另见[源码重建说明](build/REPRODUCE.md#从原始流程生成诊断内核)。
