# 早期 Core3 心跳候选与 r003 实现

本目录保留早期实现及当期约束；当前 r004 源码位于 `amp/core3-g4/`，已验证范围以 [AMP 阶段成果](../../docs/reports/amp-stage-summary-20261030.md)为准。以下“待验证”只描述本目录早期版本。

本目录不包含板端加载脚本。程序只适用于冷复位释放的 AArch64 A53-3、EL3、MMU／I／D cache 初始关闭状态。条件不符则停留，不支持热加载或 ATF PSCI CPU_ON 入口。r001 使用 Linux 驱动通过 PMU 的指定地址 wakeup 接口启动，实际部署前仍须校验配套 DT 和节点状态。

自定义启动代码不链接 standalone BSP，不执行共享 L2 set/way 维护、不操作 GIC／时钟／UART／DMA／PMU。MMU 仅映射候选私有区 [0x60000000,0x60200000) 和共享区 [0x60200000,0x60400000)，均为 NS、Inner-shareable、Normal-NC，I/D cache 保持关闭。页表保存在私有区，硬件表遍历也使用非缓存属性。TLBI ALLE3 作用于本核，不使用广播变体。

共享区只占用首个状态页，后续 Linux 映射必须匹配 Normal-NC，不能直接采用默认 Device 类型的 ioremap。共享区 XN；私有区暂以 2MiB 块映射，未细分只读代码与不可执行栈，属于验证程序，不能直接作为产品内存保护方案。

状态偏移：0 magic(u32,0x504d4143)、4 version(u32,1)、8 core(u32,3)、12 CurrentEL(u32,12)、16 counter_freq(u64)、24 boot_token(u64)、32 heartbeat(u64)、40 state(u32,1=RUNNING/2=FAULT)、64 ESR(u64)、72 ELR(u64)、80 FAR(u64)。启动和异常处理均只写 Core3 所有的状态字段；异常发生在页表设置完成前，故障记录也可能无法写出，不能把无记录解释为无异常。

boot_token 来自物理计数器，不保证跨冷启动唯一；当前只验证心跳，不是已确认的完整会话协议。计数器访问及频率是否正确仍需后续板端验证。程序无握手／回显，不构成通信通过。

配套 r001 已生成 Linux no-map DT、兼容映射和单次 PMU 加载驱动；ELF／模块／FIT 离线检查已完成。阶段执行记录见 `logs/amp/2026-10-30/g0/`。不得仅因本程序能链接便认定共存或通信通过。
