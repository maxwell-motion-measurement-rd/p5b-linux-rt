# P5 perf初测与ftrace诊断准备

日期：2026-10-29。原始RT镜像上的perf软件事件统计与采样已完成；ftrace尚未执行；独立诊断镜像已构建并通过主机静态校验，已写入SD并安全弹出，等待启动。状态见state.json。

## 本轮做了什么

板端仍运行`5.4.0-rt1-xilinx-v2020.2-p5b`，PREEMPT_RT=1、CPU0—2，未加载ble.sh。原配置支持PERF_EVENTS，未启用ARM_PMU和FTRACE。事件源只有software、breakpoint和CCI_400_r1，没有A53 PMU。板上原先没有perf命令。

使用原工程GCC9.2.0及sysroot，基于RT源码提交`e4cc2d02d270570055fe2b46ca2eb17c21938504`的tools/perf构建精简工具。首次构建因ARM64代码在NO_LIBELF下仍包含gelf.h而失败；在独立tools源码副本中将该头文件移入已有HAVE_LIBELF_SUPPORT条件分支后构建成功。补丁见[perf-no-libelf.patch](perf-no-libelf.patch)，原内核源码已跟踪文件未改动。

工具通过串口传到`/tmp/rt-audit-tools`，不安装到系统目录。SHA-256：

- 压缩包：`040d39e6240b1cbae833d0a7d051a2364010a22a4472191175aebe9bf81309ba`。
- perf二进制：`30a2751779699d825fff83fe5ad443aefcbb67a6f425108b994300c604fec571`。

`perf --version`仅输出`perf version`，版本字段为空，因此本轮按源码提交、构建日志及二进制摘要识别工具，未将空白字段作为版本证据。精简构建未启用libelf、DWARF、libunwind及脚本语言支持，板端符号解析有局限。

## perf实际结果

测量CPU均为CPU2，负载为原rtload，调度策略SCHED_OTHER。CPU模式为整数乘加循环；内存模式分配两个64MiB缓冲区，总计128MiB并反复拷贝。

| 项目 | CPU负载 | 内存负载 |
| --- | ---: | ---: |
| 负载请求时长 | 10秒 | 10秒 |
| task-clock | 9978.98 ms | 10225.37 ms |
| context-switches | 2508 | 2577 |
| cpu-migrations | 0 | 0 |
| page-faults | 44 | 32815 |
| perf退出码 | 0 | 0 |

内存统计包含缓冲区分配和首次访问等准备过程，覆盖范围大于rtload打印的循环时间，因此task-clock超过10秒不能解释成工具计时错误。page-faults为合计事件，未在本轮拆分major/minor，不能由此判断磁盘缺页或存储故障。

统计命令见[CPU命令](05-perf-stat-cpu.sh)、[内存命令](06-perf-stat-mem.sh)，实际输出分别在[CPU记录](05-perf-stat-cpu.txt)、[内存记录](06-perf-stat-mem.txt)。

另以`cpu-clock:u`、99Hz、frame-pointer调用链对CPU负载采样10秒，采到986个样本，报告显示Total Lost Samples为0，record和report退出码均为0。样本的68.26%落在rtload偏移0xcb8，31.74%落在0xcc0。板端报告未能解析这些地址的函数名；主机对相同负载二进制反汇编，定位到main内的整数乘加循环，见[指令记录](rtload-hotspot-disassembly.txt)。这些结果说明采样流程有效，不能当作项目控制算法的性能结论。

原始[perf.data](perf.data)为82492字节，已与板端SHA-256核对：`d801a574fa3263d761a8155b92883b883f3dc8eb9c9888eaa34e94baab72d302`。采样命令和报告见[07-perf-record.txt](07-perf-record.txt)，机器读取结果见[measurements.json](measurements.json)。

硬件事件检查中，`perf stat -e cycles -- sleep 1`显示`<not supported>`，但退出码仍为0。本轮按实际事件输出判为不可用，不把退出码0写成硬件PMU测试通过。instructions、cache-misses等A53硬件事件也未完成验证。

## 收尾核对

测试前后提取的418条内核日志完全一致，未新增内核消息。未发现perf统计／采样、rtload或cyclictest残留进程。SD中image.ub仍为原始摘要`f7c224640ad30359a731a5492f06769b4f081496c88fbe273022c48fd2789484`，频率策略、RT预算、perf_event_paranoid=2及kptr_restrict=0未修改。串口已释放，板子继续运行原始镜像。证据见[测试前](02-before.txt)和[收尾](08-postcheck.txt)。

本次软件采样本身有开销，与上一轮未开启perf的cyclictest结果分开记录。本轮未同步捕获此前1255／1293μs的唤醒尖峰，因此仍不能解释其根因。

## ftrace为什么还没有结果

原镜像`CONFIG_FTRACE`未启用且没有tracefs接口，不能通过安装一个用户态命令补出内核跟踪功能。独立诊断配置启用FTRACE、FUNCTION_TRACER、FUNCTION_GRAPH_TRACER、SCHED_TRACER、FTRACE_SYSCALLS及ARM_PMU；版本名追加`-diag-ftrace`。自动依赖项及全部配置差异见[diagnostic-config-diff.txt](diagnostic-config-diff.txt)。IRQSOFF_TRACER和PREEMPT_TRACER未启用，不承诺提供这两种tracer。

诊断版本保留PREEMPT_RT、三核和原DTB，重新构建内核及匹配模块，使用原始用户空间，不加载ble.sh。诊断镜像不等于原始测量基准，构建通过也不等于已通过上板验证。

后续采集脚本为[work/scripts/ftrace-short-capture.sh](../../../work/scripts/ftrace-short-capture.sh)：验证诊断版本后，以独立trace实例记录10秒调度、IRQ及softirq事件，覆盖CPU0—2，保存trace_clock及各核缓冲区统计。先确认日志和丢事件情况，再安排带负载复现。脚本尚未在板端执行。

## 来源与续接

- [执行计划](../../../docs/plans/rt-diagnostics-execution-plan.md)说明步骤和范围；本目录state.json记录实际完成情况。
- 构建脚本：[perf](../../../work/scripts/build-perf-diagnostic.sh)、[诊断内核](../../../work/scripts/build-ftrace-diagnostic.sh)。
- [Linux5.4 ftrace官方文档](https://www.kernel.org/doc/html/v5.4/trace/ftrace.html)解释tracefs、跟踪事件与缓冲区；perf行为依据匹配源码tools/perf/Documentation/perf-stat.txt和perf-record.txt，并以本轮板端输出核实可用性。
- 上一轮基准：[10分钟冒烟和短负载报告](../../rt-risk/2026-10-29/103809-tools/report.md)。

## 诊断包准备结果

独立内核、62个匹配模块和FIT已构建完成。DTB、BOOT.BIN、boot.scr与原版本逐字节比较一致。配置、rootfs保留及FIT载荷校验结果保存在[diagnostic-evidence/](diagnostic-evidence/)。编译中途为调整并行度停止过一次，随后增量续编并成功，完整构建日志保留。

最终诊断image.ub为21,510,740字节，SHA-256：`c81f2203d00dcc086fb0e42dc7e321b71f52be94bcf22f2254e37e474edbb943`。在更新模块后的1372个cpio条目全部保留的基础上，新增/opt及诊断工具目录，共6个路径；工具不会自动运行。

本地交付包：`work/artifacts/p5-ftrace-diagnostic-20261029.zip`，SHA-256：`b70357452556328797f05b3b47215c0cf13220ee3509688918e812f830aa620a`。ZIP包含诊断及原始回退image.ub、说明、源码与校验证据；已检查ZIP CRC、读回字节及所有成员摘要。包内SHA256SUMS可逐项核对。

perf测试结束时使用的是原始RT镜像。随后已完成下述SD部署；诊断内核尚未启动，ftrace与A53 PMU实测均待执行。测试工具和脚本已放入诊断镜像，重启后无需再次通过串口传输。

## SD部署结果

2026-10-29 12:17，核对用户指定F:为USB接入的FAT32卷，磁盘大小31,954,305,024字节。原三件套摘要与已知RT基准一致；先备份并校验，再只替换image.ub。最终读回21,510,740字节，摘要与诊断镜像一致，BOOT.BIN和boot.scr保持原摘要。Windows安全弹出后F:不再就绪，文件不可访问。部署记录见[sd-deployment.json](sd-deployment.json)。

备份路径：`C:\Users\13931\Documents\ChatGPT\maxwell_implementation_dual axis drive and control\work\artifacts\rt-diagnostics\sd-backup-20261029-121708`。用户需将SD卡插回断电板子，接好串口并上电；之后核对诊断版本、RT标志、三核、模块及tracefs／PMU，再运行ftrace。SD写入校验不代表启动验证通过。
