# P5 内核与通信测试可视化

本页仅使用2026-10-29的内核测试和2026-10-30的Linux与Core3通信实验已有数据。没有新增上板测试，没有使用模拟数据、拟合曲线或补造缺失值。

## 内核唤醒延迟

![内核延迟统计](figures/test-results-20261031/01-kernel-latency.png)

原始RT测试中，CPU首测与内存负载的最大唤醒延迟分别为1255µs、1293µs，严格超过1000µs的样本分别为1个、2个。CPU复测没有再次出现超过1ms的样本，不能据此认定问题已经消失。

空载测了600秒，其余各60秒；最大值不能当作严格的场景性能排名。1000µs是测试线程的探针周期，尚未确定为产品截止时间。

![内核延迟分布](figures/test-results-20261031/02-kernel-distribution.png)

左图显示主要分布，右图展开尾部；右图纵轴采用对数刻度，让少数尖峰仍可见。四组分布均来自1µs原始直方图，不具备逐样本时间顺序，因此不绘制伪造的时间趋势。

来源：[机器汇总](../../logs/rt-risk/2026-10-29/103809-tools/measurements.json)、[T00](../../logs/rt-risk/2026-10-29/103809-tools/T00-histogram.txt)、[CPU](../../logs/rt-risk/2026-10-29/103809-tools/CPU-histogram.txt)、[MEM](../../logs/rt-risk/2026-10-29/103809-tools/MEM-histogram.txt)、[CPU复测](../../logs/rt-risk/2026-10-29/103809-tools/CPU-repeat-histogram.txt)。

## Linux与Core3通信事务耗时

![通信耗时统计](figures/test-results-20261031/03-communication-latency.png)

P99（99th Percentile，第99百分位数）表示约99%的样本不超过该值。本图分位数沿用原测量的最近秩计算，纳秒结果截断为整数微秒。

空载、CPU负载、内存负载各30分钟；每种条件依次进行正向、反向、交叉测试，各10分钟、60000笔。九组共540000笔，目标发送频率为100Hz。反向与交叉测试包含两步交互，反向测试由Linux指令触发。

内存负载条件下交叉完整事务最大观测耗时为4024µs。通信事务耗时与前面的线程唤醒延迟测量范围不同，不直接比较为内核性能的改善或退步，也不能将有限实测最大值当作已证明的最坏上界。

![通信耗时分布](figures/test-results-20261031/04-communication-distribution.png)

每条累计曲线均使用全部60000笔数据；未抽样、拟合或插值。CPU负载为三核普通整数负载，内存负载为三个各256MiB的填充／复制／比较进程，与早期内核短测的负载配置不同。

来源：[长测汇总](../../logs/amp/2026-10-30/g5/pressure-results.json)、[完整证据包](../../logs/amp/2026-10-30/g5/amp-g5-evidence.tar.gz)、[本次制图数据表](figures/test-results-20261031/communication-metrics.csv)。

### 正确性与恢复结果

| 已执行项目 | 现有记录 |
| --- | --- |
| 正常长测 | 540000笔；新增通信错误0，missed_release为0 |
| Linux测试程序重启 | 10次，每次恢复后100笔回显成功 |
| 通信服务状态重置 | 10次，每次恢复后100笔回显成功；不等同于硬件复位Core3 |
| 冷启动 | 5次，每次300笔，共1500笔，通信错误0 |
| 冷启动采集缺口 | 第5次缺少FSBL／U-Boot日志，保留Linux部分启动日志与通信验证证据 |

以上是有限实验样本的结果，不表示失效率必定为0。故障注入阶段会主动产生超时与拒收，不能与正常长测的“新增错误0”混为一谈。冷启动均按人工重载流程执行，自动启动仍暂缓。

来源：[G5结果](../../logs/amp/2026-10-30/g5/results.json)、[冷启动结果](../../logs/amp/2026-10-30/g5/cold-results.json)、[完整测试报告](amp-g5-validation-20261030.md)。

## 诊断内核跟踪

![诊断跟踪结果](figures/test-results-20261031/05-diagnostic-trace.png)

完整复测记录220415条事件，各核覆盖／丢弃计数为0。目标线程的唤醒事件到调入匹配30001对，平均间隔约3.28µs，最大5µs。这是局部路径间隔；同期cyclictest完整唤醒延迟最大为86µs，两者不矛盾。

这里仅展示16MiB／核的10秒空载完整复测；首次4MiB缓冲区发生覆盖，未混入完整统计。诊断内核、跟踪开关、负载、时长与原始RT短测不同，不能据此认定1255／1293µs尖峰已经修复。

来源：[事件分析](../../logs/rt-diagnostics/2026-10-29/board-trace/trace-analysis.json)、[原始跟踪归档](../../logs/rt-diagnostics/2026-10-29/board-trace/report.md)。

## 数据核验与复现

制图脚本：[visualize-test-results.py](../../work/scripts/visualize-test-results.py)。脚本核对4份原始直方图摘要、样本数、分位数、最大值及超过1000µs的样本数；核对通信证据包摘要，并从540000笔原始延迟重新计算九组统计，与板端汇总逐项比对；核对完整跟踪的事件总数与缓冲区统计。

[来源摘要与核验记录](figures/test-results-20261031/provenance.json)记录每份制图输入的SHA-256（文件内容摘要）。PNG用于直接查看，同名SVG适合放大或排版。SVG和PNG使用同一组数据。

本机重现命令（需要Python、NumPy与Matplotlib，中文字体使用Microsoft YaHei）：

```powershell
python -m pip install --target work/plot-deps matplotlib numpy pillow
python work/scripts/visualize-test-results.py
```

图表生成与文档同步不涉及板端操作，原始证据保持不变。当前结果仍不能替代真实控制任务、业务截止时间与电机闭环验收。
