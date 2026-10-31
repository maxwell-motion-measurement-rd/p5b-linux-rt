# P5 原始 RT Linux 冒烟测试与短负载执行结果

记录日期：2026-10-29，Asia/Shanghai。归档时间：2026-10-29T11:06:54.878354+08:00。

## 当前结论

按本轮短测范围，已完成10分钟空载冒烟测试、60秒CPU负载、60秒内存负载及一次60秒CPU复测。测量和负载程序均正常退出，前后内核日志一致，未观察到新增内核错误。

CPU与内存负载下分别出现1255 μs、1293 μs的唤醒延迟。CPU复测最大641 μs，但这60秒没有再次出现大于1 ms的样本，不能证明问题已消失。当前结果支持继续调查，尚不足以认可该内核组合的完整兼容性或产品实时指标，也不足以认定必须升级5.4.3。

源码审查同时发现futex退出路径与JBD2稳定修复需要优先核对，详见[source-audit.md](source-audit.md)。本轮没有改内核或应用这些补丁。

空载冒烟测试（smoke test）是初步运行检查：不额外施加 CPU、内存等压力负载，让 cyclictest 运行 10 分钟，记录唤醒延迟，并检查程序退出状态及测试前后内核日志。系统服务、内核线程和测量程序仍在运行，因此“空载”不表示 CPU 使用率为零；这项检查不能替代长期稳定性测试或产品实时验收。

## 基准与现场

- 实板为P5 XCZU4EV，软件工程保留P5B名称。Linux使用CPU0—2；未启动Core3裸机，未连接或驱动电机。
- 运行内核为`5.4.0-rt1-xilinx-v2020.2-p5b`，`/sys/kernel/realtime=1`，CPU online为`0-2`。
- 上一阶段已核对SD启动文件、运行配置和Bash摘要。本次收尾复核`image.ub` SHA-256仍为`f7c224640ad30359a731a5492f06769b4f081496c88fbe273022c48fd2789484`。没有重新启动捕获完整U-Boot日志，也没有逐文件校验整个运行rootfs。
- 采用原始RT镜像的Shell，保留原镜像自带Bash；BLE_VERSION未设置。没有加载ble.sh或自定义启动环境。
- 保持原有`userspace`频率策略，观测频率1199999 kHz；RT period/runtime保持1000000/950000 μs。没有修改CPU隔离、IRQ亲和性、PM QoS、DTB、bitstream或启动参数。
- 串口COM3，115200、8N1、无流控，所有命令和结果已落盘，操作结束后串口已释放。板端RTC日期不正确，本轮未校时；文件日期采用主机时间，测试持续时间采用单调时钟。

## 工具和测量方法

原Ubuntu虚拟机的SSH已恢复，使用原工程GCC9.2.0与sysroot构建ARM64工具。初次rt-tests1.10在板端NUMA初始化时失败，退出码1，尚未进入测量；保留失败工具和日志。这是工具适配问题，未计作内核性能失败。

实际测量使用kernel.org上游rt-tests1.0，构建选项`NUMA=0`，未修改其测量代码。工具、负载程序、源码和构建说明见[tool-build-and-run.md](tool-build-and-run.md)、[sources/](sources/)及[binaries/](binaries/)。最终cyclictest SHA-256为`131c6a2d9fff8950a48939e970a82ec819d5bca06e98371f5dd1d0333b9ace6c`；rtload为`441fcb946f6a9e4b5ce53055d9c055abb7902db802244b616fa5416e7e61ac3d`。

所有主测量均使用以下参数，DURATION在空载冒烟测试中为`10m`，短负载中为`60`：

```sh
/tmp/rt-audit-tools/cyclictest --laptop -a1 -t1 -p80 --policy=fifo -m -i1000 -DDURATION -q -h2000
```

测量线程固定在CPU1，SCHED_FIFO优先级80，CLOCK_MONOTONIC绝对睡眠，间隔1000 μs，mlockall，直方图上限2000 μs，静默输出。上游此版本的`--laptop`跳过cpu_dma_latency写入，使本次保持原有休眠条件。串口低频采样也会产生背景开销，未在本轮剔除。

CPU场景由两个普通SCHED_OTHER进程分别在CPU0、CPU2执行整数运算；中途/proc/stat采样确认两核接近满载。内存场景在CPU2分配两个64 MiB缓冲区，合计128 MiB，反复拷贝。负载均有限时长。源码为[sources/rtload.c](sources/rtload.c)，该负载只覆盖这些动作，不等同于stress-ng的全套压力场景。

先行5秒工具自检取得5000个样本，min/avg/max为43/46/52 μs，退出码0，无直方图溢出。

## 测量结果

以下延迟单位均为μs。平均值采用cyclictest打印的整数平均值；P99/P99.9由直方图按最近秩计算，为1 μs桶值。

| 场景 | 时长s | 样本数 | 最小 | 平均 | P99 | P99.9 | 最大 | 严格大于1000 μs的样本 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T00 | 600 | 600000 | 43 | 46 | 48 | 49 | 364 | 0 |
| CPU | 60 | 59999 | 41 | 46 | 48 | 53 | 1255 | 1 |
| MEM | 60 | 59998 | 44 | 58 | 70 | 73 | 1293 | 2 |
| CPU-repeat | 60 | 60000 | 43 | 46 | 47 | 50 | 641 | 0 |

四个场景均无直方图溢出，测量及负载退出码全部为0。各直方图已从板端导出并与板端SHA-256核对；可机器读取的汇总见[measurements.json](measurements.json)。原始数据分别为[T00](T00-histogram.txt)、[CPU](CPU-histogram.txt)、[MEM](MEM-histogram.txt)、[CPU-repeat](CPU-repeat-histogram.txt)。

1000 μs是本轮探针周期及用于观察尾部的分界值，尚未定义产品业务截止时间。cyclictest测的是周期线程唤醒延迟，不能替代命令解析、轨迹规划、核间通信或电机控制的端到端验收。空载和负载观测时长不同，这些最大值不能作为严格的场景性能排序，也不能据此归因于RT移植。

## 逐步执行及结果

| 步骤 | 实际执行 | 结果／证据 |
| --- | --- | --- |
| S02/S03 | 基准与硬件盘点 | 见[上一阶段报告](../102244-serial/report.md)与[硬件清单](../102244-serial/hardware-inventory.md) |
| S04 | 恢复构建入口、构建、串口传输及摘要校验 | 已完成；1.10 NUMA失败后，1.0 NUMA=0自检通过；01—06日志及工具说明 |
| S05/T00 | 10分钟空载冒烟测试 | 已完成；07、08系列、12日志及T00直方图 |
| S06/T02短测 | CPU0/2负载60秒 | 已完成短测；13—15、17日志；1个样本超过1 ms |
| S06/T03短测 | CPU2内存负载60秒 | 已完成短测；16、18、19日志；2个样本超过1 ms |
| S08短复测 | 原参数CPU场景再测60秒 | 已完成该次复测；20—23日志；本次未超过1 ms，尖峰原因未解决 |
| 收尾 | 进程、退出码、镜像、策略、内存、温度、dmesg只读复核 | [24-postcheck.txt](24-postcheck.txt)、[postcheck.json](postcheck.json) |
| S09 | 保存结果、边界、源码风险及续接状态 | 本报告、manifest.json、SHA256SUMS及计划状态文件 |

收尾未发现cyclictest或rtload残留进程，MemAvailable为3905252 kB。PS温度收尾约58.5℃，此前采样约57—60℃；来自IIO AMS原始值换算，只代表采样时刻，未指定温度验收线。测试前后dmesg提取的418条内核记录完全一致；未发现panic、Oops、BUG或Call trace。原有视频、时钟、VCU、SPI NOR、/dev/root和eMMC FAT提示仍保留，未在本次修复。

## 源码风险与未完成项目

厂商基线为`62ea514294a0c9a80455e51f1f4de36e66e8c546`，RT提交为`e4cc2d02d270570055fe2b46ca2eb17c21938504`。源码Makefile仍为5.4.0；不能因补丁名含5.4.3，就认为5.4.1—5.4.3稳定修复已全部包含。

只读核查指出futex PI owner退出活锁、robust非PI退出唤醒、futex exec/exit清理系列，以及JBD2空间计数下溢是优先审查项。已有当前源码形态与官方修复的差异证据，但仍需核对厂商等价实现、系列依赖及应用触发条件。这些差异尚未被证明是该RT移植的硬性前置，也不能由cyclictest排除。

- T01正式空载、T02/T03原建议30分钟场景、T06联合负载及原建议4小时长测均未完成；本轮范围限于冒烟测试和短负载验证。
- 网络无确认链路及对端，未做网络负载。无健康的专用测试存储，eMMC有FAT提示，未做存储写压力。
- 原始配置`CONFIG_FTRACE`未启用，本轮没有追踪尖峰调用路径。需要trace时另做诊断镜像，与原始基准分开编号。
- 未覆盖Core3/AMP、DMA数据路径、EtherCAT时序、产品核心板、电机和业务截止时间；也未建立非RT对照。

## 下次从哪里继续

1. 先读本报告与[测试方法与结果](../../../../docs/reports/rt-assessment-summary-20261029.md)，重新核对板端镜像、环境和临时工具是否仍在。重启会丢失/tmp。
2. 优先审查futex退出相关修复系列与JBD2差异，确认项目是否使用PI/robust mutex及相关退出方式，形成针对该厂商RT树的修复决策；保留当前镜像作为对照基准。
3. 针对已观察到的尾部延迟，制定可记录尖峰上下文的诊断方案。若启用FTRACE，使用独立诊断镜像并保留配置差异，再复现实验；本轮结果不能直接定位到某个驱动或IRQ。
4. 定位与必要修复后，再安排更长的空载、分项及联合负载回归。业务周期和截止时间需由项目明确后单独验收。

临时工具和板端结果保留在`/tmp/rt-audit-tools`、`/tmp/rt-audit-run`便于后续复核；主机已有完整导出。板子和Ubuntu虚拟机未被关机，未创建定时任务，串口已释放。

## 来源与复核

- 本机一手证据：本目录编号命令及串口日志、导出的直方图、工具源码与二进制、[前阶段基准清单](../102244-serial/manifest.json)。
- 上游工具源码：[rt-tests1.0归档](https://cdn.kernel.org/pub/linux/utils/rt-tests/older/rt-tests-1.0.tar.xz)，本地快照位于sources/，源码XZ SHA-256为`aea85fd8eda8c1d96e9d32a019bfd4a1d2e0d362971d97838996f49d1af2d470`。
- 源码修复依据：[Linux5.4.3累计stable补丁](https://cdn.kernel.org/pub/linux/kernel/v5.x/patch-5.4.3.xz)、[ChangeLog-5.4.1](https://cdn.kernel.org/pub/linux/kernel/v5.x/ChangeLog-5.4.1)、[ChangeLog-5.4.3](https://cdn.kernel.org/pub/linux/kernel/v5.x/ChangeLog-5.4.3)，具体提交与本地证据见[source-audit.md](source-audit.md)。
- 本目录全部归档文件的校验值在[SHA256SUMS](SHA256SUMS)。计划中的初始建议与实际执行以本报告、manifest及状态文件区分。
