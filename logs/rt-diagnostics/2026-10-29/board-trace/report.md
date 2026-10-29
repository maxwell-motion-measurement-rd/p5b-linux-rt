# P5诊断内核启动、ftrace与A53 PMU实测

日期：2026-10-29。本轮已完成诊断内核启动核对、两次10秒空载事件跟踪和一次10秒硬件计数。第一次跟踪存在缓冲区覆盖，扩大缓冲区后重新采集，第二次事件完整。此前原始RT负载下超过1ms的尖峰尚未定位。

## 运行对象与条件

实板为P5 XCZU4EV，运行`5.4.0-rt1-xilinx-v2020.2-p5b-diag-ftrace`，PREEMPT_RT=1、CPU0—2，Core3未启动裸机，未驱动电机。SD中image.ub的SHA-256为`c81f2203d00dcc086fb0e42dc7e321b71f52be94bcf22f2254e37e474edbb943`。原启动参数、userspace频率策略、观测频率1199999kHz及RT预算1000000/950000µs保持。没有加载`ble.sh`。

运行配置确认FTRACE、FUNCTION_TRACER、FUNCTION_GRAPH_TRACER、SCHED_TRACER、FTRACE_SYSCALLS和ARM_PMU已启用。工具摘要与交付包一致，dmaproxy和xlnx_vcu_core已加载，启动日志确认armv8_pmuv3驱动提供7个计数器。验证范围为当前内核版本、运行配置、CPU、模块、镜像摘要和dmesg；本轮未重新捕获完整FSBL／U-Boot早期启动输出。

首次COM3访问被占用的MobaXterm会话阻塞，释放串口后恢复。所有实际测试通过COM3、115200、8N1、无流控执行。

## ftrace实际执行

使用独立trace实例，`current_tracer=nop`，仅启用以下事件：sched_waking、sched_wakeup、sched_switch、irq_handler_entry/exit、softirq_entry/exit。记录覆盖CPU0—2，明确选用`mono`时钟。此次使用事件跟踪，没有运行function或function_graph tracer，也没有测量所有锁或所有内核函数。

cyclictest单线程绑定CPU1，FIFO80、1ms周期、mlockall，使用`--laptop`跳过cpu_dma_latency写入，直方图上限2000µs，静默输出。本轮未叠加额外CPU或内存压力。

| 记录 | 请求时长 | 每核缓冲区 | cyclictest样本 | 最小／平均／最大µs | ftrace完整性 |
| --- | ---: | ---: | ---: | --- | --- |
| 第一次 | 10秒 | 4MiB | 10000 | 62／74／85 | CPU1 overrun=139280，前段历史已被覆盖 |
| 完整复测 | 10秒 | 16MiB | 10000 | 63／74／86 | 各核overrun、commit overrun、dropped events均为0 |

两次脚本退出码均为0，cyclictest直方图均无溢出。第一次的cyclictest统计与其不完整的事件历史分别保留，不能将那份事件日志当作完整10秒观测。两次实例名、脚本、参数与结果见编号命令／串口日志，以及[exported/](exported/)。基础镜像内脚本使用默认时钟和4MiB缓冲，本轮在/tmp副本中选择mono；复测再修改实例名、输出目录和缓冲区，未改写镜像内脚本。仓库中的后续采集脚本已将16MiB及mono设为默认值；现有诊断ZIP和板内旧脚本的摘要保持，使用时需区分版本。

## 完整日志看到了什么

复测共解析220415条事件，恰好等于三个CPU缓冲区entries之和，解析器未丢弃事件行。其中sched_switch 86043条、sched_waking及sched_wakeup各43426条、IRQ进入／退出各11676条、softirq进入／退出各12084条。IRQ处理器进入记录均为arch_timer；softirq以HRTIMER为主。这只描述本次空载窗口的活动构成，不能说明其他工作负载下没有外设中断影响。

通过CPU1的cyclictest唤醒频次识别测量线程PID988；其调度优先级字段为19，与FIFO80相符。匹配该线程的sched_wakeup和后续sched_switch，得到30001对事件，间隔最小2µs、平均约3.28µs、P99为4µs、P99.9与最大值为5µs。文本时间戳显示到1µs，统计按该输出计算。

这30001对事件不等于30001个测量周期。日志在部分周期附近可见cyclictest以D态让出CPU、ksoftirqd/1运行、cyclictest再被唤醒和调入的多次往返；同一个测量线程在一个周期内可以出现多次唤醒。5µs只表示所匹配事件之间的调度等待，不能替代86µs的完整周期唤醒延迟、算法执行时间或已证明的最坏情况上界。

最大片段见[事件上下文](rt-ftrace-idle2-worst-dispatch-context.txt)，完整计数与计算结果见[trace-analysis.json](trace-analysis.json)，分析脚本为[analyze-ftrace-capture.py](../../../../work/scripts/analyze-ftrace-capture.py)。本轮只采调度和中断事件，尚不足以确定D态往返对应的具体锁或调用路径，更不能把它直接认作原始RT负载尖峰的原因。

## A53硬件计数结果

在停止跟踪后，以CPU2上的普通SCHED_OTHER整数运算负载验证PMU，时长10秒。

| 事件 | 实际数值 |
| --- | ---: |
| task-clock | 9961.98ms |
| cycles | 11943565134 |
| instructions | 7956337962 |
| cache-misses | 144742 |
| branch-misses | 376226 |

perf退出码为0，上述硬件事件均有数值，显示运行比例100%，约0.67 instructions/cycle。PMU中断计数在CPU2增加。原始RT镜像上的cycles此前显示not supported；此次可用结论限定于启用了ARM_PMU的诊断版本。它验证计数功能，不代表项目控制算法的性能达标，也不由miss次数单独推算命中率。原始输出见[05-pmu-stat.txt](05-pmu-stat.txt)。

## 数据完整性与收尾

板端证据包1056409字节，SHA-256为`ec276614e49400ebc621b2e029a79089df03d97dc84472acf26bb36f6f61dbf8`。第一次连续十六进制导出少218字节，校验失败，未用于分析；失败记录保留在[transfer-attempt1.json](transfer-attempt1.json)。随后改用16KiB分块、逐块长度／SHA-256校验，并核对整个文件摘要后接受数据。65块中第31块（从0编号）重试一次后通过，其余块首次通过。65块中第31块（从0编号）重试一次后通过，其余块首次通过。两份解压后的trace文本也与板端原文摘要一致。分块记录见[trace-evidence.tar.gz.json](trace-evidence.tar.gz.json)，原始证据包为[trace-evidence.tar.gz](trace-evidence.tar.gz)。

测试前后421条内核日志完全一致，未新增内核消息；原有视频、时钟、VCU、SPI NOR和eMMC FAT等提示仍保留，本轮未修复。收尾未发现cyclictest、rtload或perf测试进程。两个测试trace实例的采集及事件已关闭，导出校验完成后成功移除实例、释放环形缓冲区；全局tracer保持nop，全局事件未启用，tracefs挂载保留。板端/tmp原始文件保留，串口已释放。

## 结论与下一步

诊断内核已能启动，ftrace事件采集和A53硬件计数已实际验证。复测10秒内未观察到超过1ms的唤醒延迟，但这次为空载且启用了诊断能力，不能用86µs与此前原始RT的1255／1293µs直接比较，更不能认定负载尖峰已经解决。

后续应在诊断版本下逐项复现CPU／内存负载，采用足够的缓冲区或按任务过滤事件；若捕获到尖峰，再结合对应时间段的调度、中断及必要的函数／锁路径缩小原因。源码futex／JBD2修复差异仍需独立审查。闭环控制、AMP通信、真实外设数据通路、长时间负载及产品截止时间尚未验收。

板子目前保留诊断内核。恢复正式原始RT基准时，需要正常关机、断电并恢复已备份的原image.ub；关闭跟踪本身不会把诊断内核变回原始内核。

来源：本目录实际串口记录、经过摘要校验的事件日志、[Linux5.4 ftrace文档](https://www.kernel.org/doc/html/v5.4/trace/ftrace.html)及匹配源码tools/perf文档。准备与部署记录见[上一阶段报告](../report.md)，原始RT测量见[冒烟和短负载报告](../../../rt-risk/2026-10-29/103809-tools/report.md)。
