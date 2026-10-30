# G0 首次执行记录

本文件记录首次审查时点。后续已实现并离线编译 Linux 管理的 PMU 单次加载路径，生成心跳实验包；最新进展见 [r001 实验说明](../../../../docs/plans/linux-core3-communication/heartbeat-r001.md)。首次“未通过”的记录保留，不表示后续未进行适配。

日期：2026-10-30。用户已要求开始执行方案，并要求每一步前后反馈。此前仅制定方案、不操作板子的限制已由本次执行指令更新；本次实际板端动作仅为串口只读核查。

## 结果

G0 暂未通过，G1—G5 未执行。确认存在 Core3 启动源码路径，但尚未形成满足方案约束的共存实现及完整资源表。本结果不是认定 A53 AMP 无法实现。

## 已完成

1. 核对本地方案、SSH 配置和串口工具。
2. SSH 成功连接 Ubuntu，发现原工程、XSA、启动组件和裸机编译器。
3. 从原工程下载缓存读取固定提交的 FSBL／standalone 源码，核对次核交接。
4. COM3、115200 串口读取当前系统身份、CPU 集合、启动参数、内存资源及相关 dmesg。
5. 检查 standalone 缓存初始化、ATF 次核路径和 U-Boot 加载地址，排除直接复用另一个 Hello World 工程的假设。

只在当前 Windows 工作区写入核查脚本和日志；Ubuntu 仅执行读取命令。没有修改虚拟机原工程、板端配置或启动介质，没有加载驱动、写物理内存、释放 Core3 或重启板子。

## 固定输入与事实

| 项目 | 核查结果 |
| --- | --- |
| Ubuntu | wang-virtual-machine，Linux 4.18.0-15-generic |
| 原工程 | /home/wang/petalinux/ALIENTEK-MP |
| embeddedsw 缓存 | build/downloads/git2/github.com.Xilinx.embeddedsw.git |
| embeddedsw 提交 | 08b9f4304d1634ed632f4276d603d834940fd55a |
| ATF 提交 | e6eea88b14aaf456c49f9c7e6747584224648cb9 |
| U-Boot 提交 | bb4660c33aa7ea64f78b2682bf0efd56765197d6 |
| 原工程及原 RT BOOT.BIN | 两者 SHA-256 均为 1459d13f776071430d11c3d1476cd0a1bbfd1476609617a72e762602675d9b9b |
| Linux 工程 system.xsa | SHA-256 6f6d739b8db1401329dd2abec4b6efe6c6a4eba3a420ab358e65b20e6e9d8231 |
| 本机另一个 Vitis system_wrapper.xsa | D:/Vivado_projects/hello_world_2/vitis/system_wrapper.xsa，SHA-256 b10baec7b68e223277cf1578a4e4cde21b0f68b9a4b488ca9c3df1de1de81164；摘要不同仅证明文件不同，尚未逐项比较硬件设计 |
| 当前板端内核 | 5.4.0-rt1-xilinx-v2020.2-p5b-diag-ftrace；不能记为原始 RT 镜像 |
| Linux CPU online | 0-2 |
| 当前 CMA | [0x68400000,0x78400000)，256MiB |
| DDR 资源 | [0,0x7ff00000)、[0x800000000,0x880000000)；当前仍属于 Linux 资源布局，不能视为空闲区 |
| SD FIT 加载地址 | 原 boot.scr 为 0x10000000 |

## 源码依据和未决项

原 BIF 只有 A53-0 的 FSBL、ATF／U-Boot、PMUFW、PL 和 DTB，无 A53-3 裸机分区。

embeddedsw 的 lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c 第 287—327 行包含 A53-3 上电及复位释放，第 675—688 行写 RVBAR3，第 859—918 行完成非当前核的交接调用。说明 FSBL 具有所需基础，但不能推导现有 BOOT.BIN 已配置该载荷。

lib/bsp/standalone/src/arm/ARMv8/64bit/gcc/boot.S 第 239—240 行调用 invalidate_dcaches，第 401—445 行读取 CLIDR 并遍历缓存层级，以 dc CISW 执行 set/way 操作。必须裁剪／替换并审查启动与退出路径，不能原样在共存实验中使用。其异常级别、页表、栈、向量和定时源也需与最终启动方式一致。

ATF 的 plat/xilinx/zynqmp/aarch64/zynqmp_helpers.S 中次核冷启动路径按固件的 CPU_ON 模型处理；plat_psci.c 的 suspend 路径会调用 PMU。当前尚未证明独立 Core3 程序与这一生命周期及电源管理的协调关系。此处是未决条件，不是已观察到的掉核故障。

本地 Hello World 工程是 standalone_psu_cortexa53_0，主程序调用 init_platform、串口打印、cleanup_platform 后返回；不是已准备好的 Core3 共存载荷。不同 XSA 也需核对 DDR／PS／PL 配置，不能直接替换当前 Linux 硬件输入。

尚未完成全启动过程内存表：尤其 U-Boot 重定位／堆、FIT 解包／搬移、initramfs、固件占用与最终 Core3 ELF／页表／堆栈。没有给任何 DDR 地址授予可写或可部署结论。

## 后续工作

继续主机离线工作时，应先形成最小 Core3 启动代码及静态审查材料，消除全局缓存／GIC／平台初始化，明确异常级别、PMU／PSCI 约束；同时完成全部地址区间检查。上述项闭合后才可更新 G0 为通过、进入独立实验包构建。保持既定 A53 Core3 分工；若发现必须改变架构，另行讨论，不能自动改用 R5／Hypervisor。

## 证据

- [source-audit.txt](source-audit.txt)：可重放审查脚本的输出，包括版本、摘要、原 BIF、源码行号、启动脚本及环境地址。
- [board-baseline.txt](board-baseline.txt)：串口原始输出。
- [board-baseline.cmd](board-baseline.cmd)：实际板端只读命令。
- [审查脚本](../../../../work/scripts/amp-g0-audit.sh)：仅执行读取操作。
