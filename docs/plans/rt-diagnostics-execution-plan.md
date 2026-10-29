# P5 ftrace与perf诊断执行计划

日期：2026-10-29。用户已授权开展ftrace和perf测试。本阶段定位工具能力与初步观测，不替代产品或闭环控制验收。

当前结果：诊断版本已上板，10秒ftrace空载复测无缓冲区覆盖／丢事件，A53硬件计数已验证；首次采集覆盖、传输重试及范围限制详见[板端报告](../../logs/rt-diagnostics/2026-10-29/board-trace/report.md)。此前原始RT负载尖峰仍需复现定位。

## 原始环境与限制

板端确认5.4.0-rt1-xilinx-v2020.2-p5b、realtime=1、CPU0—2，BLE未设置。CONFIG_PERF_EVENTS=y、CONFIG_ARM_PMU未启用、CONFIG_FTRACE未启用。事件源只有software、breakpoint和CCI_400_r1。原镜像不能直接运行ftrace或使用A53硬件性能计数器。

## 本轮顺序

1. 保存能力盘点及测试前内核日志，核对原image.ub与rtload摘要。
2. 使用原工程GCC9.2.0及匹配sysroot构建perf。工具放到/tmp并核对SHA-256，不安装系统包。
3. 在原始RT镜像上做CPU和128MiB内存负载各10秒的软件事件统计；另做10秒、99Hz的CPU软件采样。单独验证cycles不可用的限制，预期失败与性能故障分开记录。
4. 收尾核对进程、内核日志及启动镜像，导出结果。
5. 在独立目录构建诊断内核与匹配模块，启用ftrace、调度／IRQ事件和ARM_PMU，版本名追加-diag-ftrace。保持PREEMPT_RT、三核及原DTB；不将诊断结果混入原基准。
6. 诊断镜像静态校验完成后，正常关机，由用户将SD卡接入电脑以便备份和替换；重新接板启动后先核对版本，再运行10秒ftrace采集。当前仍运行原镜像，不在运行过程中拔卡。

## 诊断采集与边界

脚本：work/scripts/ftrace-short-capture.sh。它会验证诊断版本、PREEMPT_RT和CPU0—2，使用独立trace实例，采集sched_waking、sched_wakeup、sched_switch、IRQ及softirq的进入退出事件，记录trace_clock和各CPU缓冲区统计，完成后关闭本实例事件。先做10秒空载采集；确认日志完整、无overrun后再设计带负载复现。

perf当前精简构建未启用libelf、DWARF、libunwind等依赖，函数符号及调用链解析有局限。软件事件和样本产生均需板端验证，不把工具编译成功写成测试通过。软件采样产生额外开销，与之前未采样的cyclictest结果分开记录。

## 续接位置

本轮日志：logs/rt-diagnostics/2026-10-29/。具体完成状态以该目录report.md及state.json为准。原10分钟冒烟与短负载基准见logs/rt-risk/2026-10-29/103809-tools/report.md。

来源：[Linux5.4 ftrace文档](https://www.kernel.org/doc/html/v5.4/trace/ftrace.html)、匹配厂商内核tools/perf源码和Documentation/perf-stat.txt、Documentation/perf-record.txt，以及本轮板端串口记录。
