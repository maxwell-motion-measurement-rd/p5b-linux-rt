# P5 原始 RT Linux 风险评估执行计划

更新日期：2026-10-29。当前状态：**S04工具准备和S05十分钟冒烟已完成，S06完成CPU／内存各60秒短测，CPU另复测60秒；负载下已观察到超过1 ms的延迟，原因未解决**。[最新执行报告](../../logs/rt-risk/2026-10-29/103809-tools/report.md)与[状态文件](rt-risk-assessment-state.json)保存实际结果。本轮范围为冒烟和短负载验证，长测未执行。续接时先读报告和状态，再核对现场。

## 1. 评估边界

- PREEMPT_RT 是项目必选条件，不建立、不执行非 RT 对照测试。
- 首轮交付源码风险清单、可追溯的 RT 测试结果和继续／修复／升级建议，不作产品实时性能合格结论。
- 同事4.9完整工程及测试材料未齐，不阻塞当前组合评估；后续取得时按完整RT组合比较。
- 首轮只在P5学习板运行Linux Core0／1／2，Core3不启动裸机，不带电机。AMP共存、真实通信及产品核心板分别验收。
- 以原始RT镜像及其原有登录Shell作为标准，不加载ble.sh，不使用后加的高亮启动器、profile钩子或自定义交互Bash环境。原始镜像自带的Bash保留。
- 先测现有RT配置，记录实际值；覆盖空载、CPU、内存和核验后可用的网口／测试存储负载。问题定位时单因素变更，改动后另编号。
- 必要修复缺失、可重现内核错误、失去进展或必需接口故障应阻止直接进入下一阶段。单次延迟偏大先定位、复测，不自动升级。
- 本轮执行范围为冒烟与短负载验证；联合及长时负载另行安排。

10分钟冒烟、30分钟分项及4小时联合负载为规划值，不是产品验收要求。实际已执行时长与未覆盖项目以报告为准。

## 2. 正式基准的精确身份

已在主机内存中只读核验两个归档包的条目，结果一致；这不代表当前SD卡已经恢复该版本。

| 项目 | 固定值 |
| --- | --- |
| 实板 | P5，XCZU4EV；P5B保留为软件工程名称 |
| 首选归档 | work/artifacts/p5b-rt-sd-20261027.zip |
| ZIP SHA-256 | a1a684b678e5eb82a4d04cdbbbdf7e5279792cd257f32674c71b33f285f840a7 |
| 镜像条目 | rt/image.ub |
| 镜像大小 | 19,501,100字节 |
| image.ub SHA-256 | f7c224640ad30359a731a5492f06769b4f081496c88fbe273022c48fd2789484 |
| 同字节备用条目 | work/artifacts/p5-rt-blesh-autostart-20261028.zip 内 rt-original/image.ub |
| BOOT.BIN SHA-256 | 1459d13f776071430d11c3d1476cd0a1bbfd1476609617a72e762602675d9b9b |
| boot.scr SHA-256 | 96a830a29dd3b3ba7063e6e916ead3b4df490c96c062a1854c41bd20fd4ef229 |
| 内核版本 | 5.4.0-rt1-xilinx-v2020.2-p5b |
| PREEMPT_RT／CPU | realtime=1；possible、present、online均为0-2 |
| 启动参数 | earlycon console=ttyPS0,115200 rdinit=/init rw |
| 根文件系统 | 内存initramfs；重启会丢失临时工具与结果 |
| 原始Shell | root登录Shell为/bin/sh；/bin/sh、/bin/bash均链接/bin/bash.bash |

原始rootfs未包含/opt/p5-blesh和/etc/profile.d/90-p5-blesh.sh，原/etc/profile没有ble.sh引用。单看uname无法区分原始RT镜像与后来只改rootfs的ble.sh镜像，必须结合启动文件摘要和rootfs环境核对。

原RT FIT载荷摘要：

| 载荷 | SHA-256 |
| --- | --- |
| gzip内核 | ef40de3bb4a906c605b2dfc83c3e5183b14c72736437bff44b0febc685343b58 |
| Linux DTB | 1d0528ef851e6efc3e43f031a7bac132ebf130d6c9df6a753f1bb393c58396a4 |
| initramfs | f07764dbbea5733556bc0e336a0fafdda7ebc3eb605ee96449ac852b6bc7f574 |

如果板上是ble.sh版本，临时退出高亮子Shell只证明当前会话退出了插件，不能证明运行环境已恢复原始归档。应正常关机、断电后恢复核验过的原始RT image.ub并重新启动，再开始正式测量。不得在板子运行中拔启动SD卡。

## 3. 续接入口与阶段状态

板卡具备连接条件后，按以下顺序推进。已完成的只读核查不重复做，除非输入摘要发生变化。

| ID | 阶段 | 当前状态 | 进入下一阶段前应具备的证据 |
| --- | --- | --- | --- |
| S00 | 保存计划和评估约束 | 已完成 | 本文件、状态JSON、ADR0003 |
| S01 | 固定补丁与镜像来源 | 部分完成 | 镜像字节核验已完成；厂商源码依赖审查继续 |
| S02 | 接板及原始RT身份核对 | 已完成 | 串口可操作、镜像摘要、启动日志、版本／CPU／Shell匹配 |
| S03 | 当前硬件、驱动、工具盘点 | 已完成 | 资源表、绑定情况、错误日志、工具及库版本 |
| S04 | 准备临时工具和记录目录 | 已完成 | 工具可运行、输出可导出、停止方法有效 |
| S05 | 冒烟与空载短验证 | 已完成10分钟冒烟 | 可正常停止、数据格式完整、无阻塞故障 |
| S06 | RT分项负载测试 | 部分完成：CPU／内存各60秒 | 各场景日志、参数、样本与未覆盖说明 |
| S07 | RT联合负载／延长观察 | 待执行，本轮未开始 | 按实际窗口完成的时长、组合、故障或停止原因 |
| S08 | 必要时诊断和复测 | 已做一次CPU短复测，尖峰待定位 | 单因素改动、独立版本、复现与定位证据 |
| S09 | 汇总评估与处置建议 | 已保存短测报告，整体评估未完成 | 源码风险、实测结果、可继续／需处理／未覆盖清单 |

S02不应等待全部源码审查才收集启动事实；但S09的准入建议必须披露源码审查未完成项。来源核对完成不等于源码兼容性通过。

## 4. 接板后先确认环境，不立即施压

串口此前为COM3、115200、8N1、无流控，仅作提示。实际COM号和占用情况要重新核对，先协调释放占用的串口会话。先读取输出，确认处于Linux命令行后再发送命令；不把命令发进U-Boot或仍在运行的程序。

在板端逐项执行、保存输出：

```sh
uname -a
cat /sys/kernel/realtime
cat /sys/devices/system/cpu/possible
cat /sys/devices/system/cpu/present
cat /sys/devices/system/cpu/online
cat /proc/cmdline
mount
df -h
cat /proc/meminfo
ls /lib/modules
readlink -f /bin/sh
readlink -f /proc/$$/exe
printf 'BLE_VERSION=%s\n' "${BLE_VERSION-unset}"
ls -ld /opt/p5-blesh /etc/profile.d/90-p5-blesh.sh 2>/dev/null
dmesg
```

BLE_VERSION未设置和上述路径不存在只是辅助检查，不能替代镜像身份核对。需要校验SD卡image.ub时，从mount识别实际启动分区；不预设mmc编号和挂载点。板端无摘要工具时，在关机取卡后用主机核对并保存，再上电记录启动。

只读记录CPU频率、休眠、IRQ和实时预算，不先改值：

```sh
cat /proc/interrupts
cat /proc/sys/kernel/sched_rt_period_us
cat /proc/sys/kernel/sched_rt_runtime_us
for policy in /sys/devices/system/cpu/cpufreq/policy*; do
    [ -d "$policy" ] || continue
    echo "$policy"
    cat "$policy/scaling_governor" "$policy/scaling_cur_freq" 2>/dev/null
    cat "$policy/scaling_available_governors" 2>/dev/null
done
ls /sys/devices/system/cpu/cpu0/cpuidle 2>/dev/null
```

原配置默认userspace governor，不能直接假设支持performance。此时不写isolcpus、不修改IRQ亲和性、不将实时预算设为-1、不停用CPU_IDLE。记录真实值后，必要的定位改动在S08另立记录。

## 5. 硬件无法访问：分层排查

对ZynqMP的PS片上外设和PL AXI IP，设备树通常是描述控制器及资源的重要来源。但硬件不可访问还可能是驱动、初始化、接线或访问接口的问题。USB／PCIe等总线上的许多设备由枚举发现，不要求每个外接设备都手工新增设备树节点。

| 层次 | 检查内容 | 典型结果及下一步 |
| --- | --- | --- |
| 硬件与分配 | 器件是否实际装载、供电／接线是否正确，资源归谁使用 | 物理接口不存在、资源预留给其他处理器时，Linux不能直接接管 |
| 硬件设计／启动初始化 | PS管脚复用是否配置，PL中是否真的加载匹配bitstream，地址／时钟／复位是否对应 | DT节点不会创建PL逻辑；status改为okay不能代替硬件配置 |
| 当前启动DTB | 节点、父节点状态、compatible、reg、interrupts、clocks、reset／pinctrl是否正确 | 缺失或disabled可以导致未注册；存在但资源错也会probe失败 |
| 内核及模块 | 对应CONFIG是否启用，模块是否存在、与运行内核匹配 | y为内置，m需正确模块；lsmod不显示内置驱动 |
| 匹配与probe | 设备是否注册、driver链接是否存在、日志是成功／延迟／最终失败 | compatible匹配不等于probe成功；早期-517需看后续是否恢复 |
| 用户空间接口 | 应查/sys、/dev、网络接口还是其他子系统，权限／工具是否齐备 | 没有/dev节点不等于没有设备；缺命令不等于缺驱动 |

当前归档工程已知例子：

- **按键**：DTS已有gpio-keys节点，但CONFIG_INPUT_KEYBOARD未启用，因而对应gpio-keys支持缺失。此例不是漏写设备树。
- **PS SPI0／1**：DTS均为disabled，且CONFIG_SPI_SPIDEV未启用。启用控制器还需核对实际引脚与从机，不能只改一个开关。
- **PL PWM**：DTS已有PWM@a0070000，但CONFIG_PWM未启用；还需确认xlnx,PWM-2.0对应的是哪个厂商驱动及其实际接口，不能认定有节点就该出现pwmchip。
- **PL EEPROM**：DTS已有AXI IIC和eeprom@50，相关驱动已启用；实际访问仍依赖PL设计、接线及probe，不能仅凭静态配置判为可用。

排查以**板上当前生效的设备树**为准，不能只看电脑上的DTS。第一次盘点用：

```sh
ls /sys/firmware/devicetree/base
ls /sys/bus/platform/devices
ls /sys/class/leds /sys/class/net /sys/class/rtc 2>/dev/null
ls -l /dev/i2c-* /dev/gpiochip* /dev/ttyPS* /dev/ttyUL* 2>/dev/null
cat /proc/bus/input/devices
cat /proc/partitions
```

确定某一设备的实际路径后，再读取其compatible、status、of_node和driver链接。DT属性可能是二进制，不能把reg直接cat出的乱码当成错误。没有status属性也不自动等于disabled；还需核对父节点与总线的实际处理。

例如PS SPI0节点路径与现有工程一致时，可只读查看：

```sh
tr '\000' '\n' < /sys/firmware/devicetree/base/amba/spi@ff040000/status
tr '\000' '\n' < /sys/firmware/devicetree/base/amba/spi@ff040000/compatible
```

路径不存在时先核对当前设备树结构，不创建伪节点。若板端有dtc，可导出当前树；没有则读取/sys/firmware/fdt（若可用）并在主机解析，不为了盘点先重编内核。

当前boot.scr加载image.ub中的DTB，单独替换SD上的system.dtb可能不生效。硬件修复如需改DTB、内核或bitstream，应保留原始基准，生成新版本并单独回归，不在正式基准测量中途偷偷替换。

## 6. 工具与测量纪律

先检查工具，不根据旧日志假设当前已有：

```sh
for tool in cyclictest stress-ng stress taskset chrt timeout sha256sum ip ping; do
    command -v "$tool" || echo "missing: $tool"
done
```

缺少时，用与目标ARM64用户空间匹配的工具链／sysroot准备临时包，记录源码版本、编译选项、依赖库和文件摘要。优先放/tmp/rt-audit-tools；若动态依赖缺失，按工具进程指定临时库路径，不覆盖原/lib或替换系统Shell。不能把Ubuntu的x86可执行文件直接复制给板子运行。

测量参数须在S04落成一次运行清单：工具版本及--help、CPU亲和性、调度策略／优先级、周期、预热、正式时长、直方图范围、负载线程数、内存与存储上限、温度采样和停止方式。参数未明确前不启动长测试。

实施默认方向：单个测量线程在CPU1，普通后台负载从CPU0／2开始；不修改启动隔离参数。实际CPU、线程及IRQ条件以现场核对结果为准，任何差异记入运行清单。先用短时间验证测量线程能周期休眠、终端可恢复，再延长。优先级不是越高越好，不直接照抄99；根据实际IRQ线程及工具能力确定并记录。

cyclictest应使用目标版本支持的内存锁定、有限时长、安静输出和直方图选项。先保存--help，再形成实际命令；本文不提供一条未经该工具版本核对就自动执行的整板压力脚本。

原始RT配置未启用ftrace。若需跟踪，先在原始镜像保存异常证据，再另建诊断RT镜像；诊断结果不能冒充原始RT基准数据。

## 7. 场景与建议测试参数

所有场景均使用PREEMPT_RT。初始探测周期建议1ms；250μs、100μs属于后续短周期探索，不能据其数值假定Linux已承担速度环／位置环，也不能作为未经确认的业务通过线。

| ID | 场景 | 进入条件 | 建议时长 | 必须记录 |
| --- | --- | --- | --- | --- |
| T00 | 冒烟／采集链路 | S02–S04完成，停止方法有效 | 10分钟 | 命令、工具可用性、样本完整性、退出及数据导出 |
| T01 | 空载唤醒 | 保留原启动服务，记录后台进程 | 30分钟 | 延迟分布、观测最大值、样本数和内存状态 |
| T02 | CPU负载 | 先短验证，普通优先级、固定线程与核 | 30分钟 | 各核使用率、负载参数、温度与延迟 |
| T03 | 内存负载 | 根据可用内存设定上限，不触发OOM | 30分钟 | 分配量、带宽／工作负载、MemAvailable、延迟 |
| T04 | 网络负载 | 实际网口链路和对端正常 | 每种可用场景30分钟 | 接口、流量、方向、IRQ／丢包与延迟 |
| T05 | 存储负载 | 已核对测试介质及独立文件目录 | 每种可用场景30分钟 | 介质／挂载点、文件大小、读写类型、同步方式与延迟 |
| T06 | 联合负载 | 分项无阻塞问题，确认本次可运行窗口 | 4小时，保留为延长项 | 实际组合、持续时间、资源／温度漂移、峰值与故障 |

缺网口对端、存储异常或对应驱动不可用时，场景标为blocked或not_covered，说明原因。DMA、EtherCAT和AMP当前不纳入已覆盖场景。T06未执行就保持待执行，不由T00代替。

内存负载先用保守的小份额启动，按照现场MemAvailable、原rootfs占用及工具行为确定上限。存储只使用新建的独立测试文件，不写裸设备、不格式化、不清空旧数据；旧日志有eMMC FAT警告，首轮优先健康的专用测试U盘。禁止将大量数据写入/tmp后宣称是SD／eMMC性能测试。

首轮每个场景至少保存：样本数、最小／平均／P99（若原始数据或直方图支持）、观测最大值、直方图溢出数，以及以探测周期为参考的延迟超限计数。无法由工具输出计算的分位数或计数留空，不能编造。业务deadline未确认时，不把探测周期超限计数称为项目截止时间违约率。

## 8. 停止、故障与续测

遇到panic、Oops、失去进展、OOM、存储I/O错误或明显资源耗尽，停止本次施压，保留现象与日志，进入定位。温度阈值需先核对器件额定值、散热条件及板上有效传感器；未核定前不开展无监测的长时联合负载。延迟峰值偏大先定位与复测，不据一次峰值直接升级。

只停止本次记录PID对应的工具，先用其正常退出方式；不以killall清理系统进程。串口异常时先保存主机已接收日志；仍可操作则结束负载、sync并正常关机。没有日志、退出码或停止原因的案例不能标通过。

长测试采用有限时长的工具进程，执行者以不超过60秒的工具等待分段获取进展，保持操作可中断。不要用一条阻塞数小时的调用，也不因本计划自动创建定时任务。监控低频、固定开销，避免高频串口打印影响测量；监控本身的CPU和日志开销需记录。

## 9. 证据目录和状态回写

主机新增本次运行目录：

```text
logs/rt-risk/<开始日期>/<运行ID>/
  manifest.json
  boot-and-environment.txt
  hardware-inventory.md
  tool-versions.txt
  source-audit.md
  T00/ ... T06/
  findings.md
```

运行ID由实际启动时间生成，日期使用Asia/Shanghai，不沿用计划日期冒充执行日期。每个案例保存命令、开始／结束时间、运行秒数、CPU／IRQ／频率条件、负载、工具退出码、摘要、原始日志与停止原因。板端临时数据先缓冲在有上限的独立目录，阶段结束立即导回主机并验证大小／摘要；重启前必须保存结果。

状态文件只写真实发生的状态：planned、partial、blocked、running、completed、failed、not_covered、not_triggered。partial表示仅完成该阶段的部分核查；not_triggered用于尚未需要的诊断阶段。completed代表该步骤执行完成，不自动表示业务实时合格。中断时写last_completed_step、next_step、原因、PID与证据路径。下次先确认是否有遗留进程以及镜像是否变化，再续接；不重跑已完成的主机来源核对。

## 10. 源码风险清单的当前起点

已完成：固定meta-retis来源、核验本地补丁摘要、比较kernel.org同名补丁、核验原RT镜像与无ble.sh用户空间。

已发现：本地补丁比官方补丁少一个arch/arm/kernel/smp.c中的392字节修改段，属于ARM32路径；其余字节一致。不能仅凭这点判定AArch64不兼容。官方与本地补丁摘要及差异解释见[讨论依据](rt-risk-and-amp-next-steps-20261029.md)。

尚待完成：取得含厂商父提交62ea514294a0c9a80455e51f1f4de36e66e8c546的完整源码；核对5.4.0→5.4.3修复、厂商回移、RT前置依赖和实际驱动语义。当前bundle是依赖父提交的RT增量，不能独立提供完整源码。

即使板端测试未出现异常，源码未查项和DMA／AMP等未覆盖项仍需列入报告。若确需5.4.3 RT候选，另建版本、保留当前基准、复跑适用矩阵，不以修改版本字符串代替升级。

## 11. 依据与关联记录

- [技术范围与风险说明](rt-risk-and-amp-next-steps-20261029.md)。
- [ADR0001：厂商基线与RT移植](../adr/0001-preserve-vendor-kernel-baseline.md)、[ADR0002：Linux／裸机职责](../adr/0002-linux-smp-and-bare-metal-core-boundary.md)、[ADR0003：原始RT测量基准](../adr/0003-original-rt-measurement-baseline.md)。
- [构建清单](../build/build-manifest.json)、[原RT上板记录](../board/rt-first-boot-20261027.md)、[外设学习指南](../board/peripheral-learning-guide-20261028.md)。
- 参考[核间任务调度设计](https://app.xmind.com/share/98hUlner)：任务映射和测试方法参考，不直接采用其中Linux控制环分配与8轴指标。
- [Linux 5.4驱动绑定说明](https://www.kernel.org/doc/html/v5.4/driver-api/driver-model/binding.html)：设备与驱动匹配、probe及sysfs关联。
