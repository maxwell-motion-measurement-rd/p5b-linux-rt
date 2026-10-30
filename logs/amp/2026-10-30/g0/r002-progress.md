# r002 计时器频率修复及执行记录

2026-10-30。r001 通过主机读卡器部署，实际原卡诊断镜像已备份并校验；实验镜像启动、内核／模块／固件身份、CPU0—2 和两个 no-map 区均实测正确。

PMU 初始状态为 0（FORCEDOFF），单次 request_wakeup 返回 0，随后节点状态为 1（ACTIVE）。Core3 返回 magic=504d4143、version=1、core=3、el=12，证明已执行到自定义载荷。freq=0、heartbeat=0、state=2：首版漏初始化新核频率寄存器，保护逻辑停止，不能记为共存通过。

Linux clocksource 为 arch_sys_counter，日志报告约 99.99MHz。CNTFRQ_EL0 是软件需初始化的频率信息，不是硬件调频控制；复位值不可依赖。[Arm 寄存器定义](https://documentation-service.arm.com/static/60df1943677cf7536a55ddef)

## 修复

- Linux 驱动读取当前已初始化 PE 的 CNTFRQ_EL0，检查 10—UINT32_MAX 范围，将频率及标识存入共享区后再请求 PMU 唤醒。
- Core3 校验标识及范围，写本核 CNTFRQ_EL0 并读回确认；不更改全局系统计数器频率。
- 协议版本变为 2，额外暴露 reason、host_freq、initial_freq、configured_freq。reason=1 表示输入频率无效，2 表示异常向量进入，3 表示本核寄存器读回不符。
- 软件错误分支清零 ESR／ELR／FAR，避免把未发生异常时的未知寄存器值当成异常证据。

## 离线结果

ELF、驱动模块编译及 MODPOST 成功；ELF 段仍为 [0x60000000,0x60008000)，静态范围／对齐／禁止指令检查通过。FIT 三个载荷提取比对通过，rootfs 原用户空间及元数据保留校验通过。

r002 镜像 SHA-256：a2c72f2edc680ee63c8efe3822db274ba895c88ea6eae2294ecf24993d0af499。

为减少再次换卡，本次拟在原 r001 镜像冷启动后经串口临时传入匹配的 r002 模块／固件；内核、DT 和共享区地址不变。这样测得的是 r001 基础镜像加 r002 RAM 临时载荷，不得宣称完整 r002 FIT 已完成上板验证。

- stripped 模块（仅去除调试段，vermagic 不变）：32169437a5a6e87e3fa70f1b8d7ab0635feef63809f5c2bdc89bcd532b69eede，12464 字节。
- 裸机固件：efc9fde6b2e0ad2d3d2c2fd93d0d0d7211d335cef31f7237ff06d4ac5abc1878，4192 字节。

## 当前状态

r001 没有热复位或再次唤醒。板上 SD 及两个 eMMC 分区均明确卸载成功、返回 0；挂载表无 MMC 项，之后 sync 完成并执行 poweroff。串口关机末段无最终 Power down 标志，不能补写为已观察到该标志。

用户配合冷启动后，重新捕获 FSBL／U-Boot／Linux 日志，确认原驱动未加载。r002 临时模块和固件已通过串口上传，板端大小和 SHA-256 与上述记录一致；替换 RAM 内固件并加载模块后，PMU 查询为 FORCEDOFF，随后单次显式唤醒成功。

返回 version=2、core=3、el=12；Linux 传入及 Core3 本核读回频率均为 99999000Hz，initial_freq=0，reason=0，state=RUNNING。两秒心跳增加20次，修复得到板端验证。

## 600 秒共存结果

21 个样本覆盖600.14秒，Linux始终在线0—2，Core3的token=11778836439保持不变，心跳从839增至6840，增量6001，观测频率9.9993Hz。每个样本的PMU状态为ACTIVE，软件状态为RUNNING，reason、ESR、ELR、FAR均为0。前后dmesg用cmp逐字节比较，返回0，没有新增内核日志。

本轮通过G2最小心跳共存检查。没有进行板端消息回显、故障恢复或压力测试，也没有完成5次冷启动验收；本结果不构成整个AMP通信方案通过。

当前SD仍为r001镜像，本次修复以RAM临时载荷运行，重新启动后不会自动保留。r002完整FIT已在主机生成且载荷提取比较通过，但未作为完整FIT上板启动。板子目前保持Linux三核和Core3心跳运行，模块因单次启动而保持引用，不能热卸载；没有再次复位Core3。

证据：[原始采样](r002-coexist-600s.txt)、[结构化结果](r002-coexist-results.json)、[启动结果](r002-start.txt)、[上传校验](r002-upload-verify.txt)。

下一阶段已完成消息帧编解码的主机准备：C实现与Python struct/zlib独立交叉验证315项通过，见wire-codec-validation.txt。该代码尚未集成到运行中的裸机或驱动，不能记为Linux→Core3消息通路通过。
