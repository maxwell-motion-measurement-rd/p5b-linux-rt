# 源码风险核查（只读）

2026-10-29，通过原Ubuntu构建主机检查；未应用补丁、改工作树或重编内核。

## 对象与来源

RT树/home/wang/p5b-rt-5.4.0/src的HEAD为e4cc2d02d270570055fe2b46ca2eb17c21938504，直接父为62ea514294a0c9a80455e51f1f4de36e66e8c546。原BSP linux-xlnx树HEAD为该父提交，两处已跟踪修改数为0。RT增量398文件、9545新增行、3597删除行，顶层Makefile无变更，SUBLEVEL仍为0。

官方v5.4提交219d54332a09e8d8741c1e1982f5eae56099de85存在且为vendor祖先；v5.4.3提交f7688b48ac46e9a669e279f1bc167722d5141eda对象不存在。标签缺失与对象缺失分别检查，没有仅凭缺标签作结论。

累计stable补丁来源：https://cdn.kernel.org/pub/linux/kernel/v5.x/patch-5.4.3.xz 。内存解压281572字节，SHA256为924c6489e0654ae25e40e0c09090894879567f4d27cdec93b33c828d3a9ac375。它是上游v5.4到v5.4.3稳定修复，不是RT补丁。

220个文件段逐段对vendor树做git apply --check：219段正向成功、反向失败；fs/jffs2/nodelist.c一段正向失败、反向成功，且vendor历史的343d6753e813ca7f3faa938d8034649b513bdbb9与相应撤销修复对应。这是文本适用性检查，不能将219段等同于219项语义修复均缺失。

## 应优先人工审查的差异

累计stable与RT修改相交11条路径，其中与本机更相关的8条通用／驱动路径，在RT树亦正向可应用、反向失败。优先项如下：

| 项目 | 当前代码证据 | 官方修复及意义 |
| --- | --- | --- |
| futex退出活锁 | PF_EXITPIDONE仍在；无wait_for_owner_exiting、futex_exit_mutex、futex_state | upstream 3ef240eaff36b8119ac9e2ea17cbf41179c930ba，stable fc3b55ef2c840bb2746b2d8121a0788de84f7fac；官方描述FIFO高优先级任务等待正在退出的PI owner可能活锁，FUTEX_PI已启用 |
| robust非PI退出丢唤醒 | handle_futex_death中无pending_op && !pi && !uval分支 | upstream ca16d5bee59807bf04deaab0a8eccecd5061528c，stable 82ca3ab31b9cf23b86436a85381e4c5757bc6b80；需核对应用是否使用robust mutex，不能泛化所有锁 |
| futex exec／exit状态清理系列 | sched.h、sched/mm.h、exit.c、fork.c、futex.c缺该系列的新字段和拆分调用 | upstream af8cbda2cfcaa5515d61ec500498d46e9a8247e2，stable 172b09ddc38d1b77b502df3ff7d5c925595b6026等；涉及退出锁、状态和调用次序，必须按系列核查 |
| jbd2日志空间无符号下溢 | jbd2_log_space_left仍使用unsigned long free=journal->j_free-32，无max_t夹零 | upstream add3efdd78b8a0478ce423bb9d4df6bd95e8b335，stable 1a6a96e0ff4681e579c98ed0fd16aff5f1ffadbf；EXT4/JBD2已启用，属通用稳定性修复，不是已证实RT硬前置 |

官方说明来源：[ChangeLog-5.4.1](https://cdn.kernel.org/pub/linux/kernel/v5.x/ChangeLog-5.4.1)、[ChangeLog-5.4.3](https://cdn.kernel.org/pub/linux/kernel/v5.x/ChangeLog-5.4.3)。

相交路径还包括PowerPC／x86架构文件、FUSE和PL011。前两类架构不用于本机，FUSE未启用；PL011是否参与运行需看绑定，本机控制台为Xilinx PS UART。

## 结论边界

已证明源码对象、文本差异及一项vendor历史对应；尚未证明这些差异都是当前RT补丁的必要前置，也没有穷尽厂商等价实现或修复系列的依赖。下一步应审查上述锁／退出语义、实际应用使用条件及修复整合路径。cyclictest通过也不能覆盖这些退出竞争场景。

本轮不据此直接升级。若确认需要修复或另建5.4.3 RT候选，须保留原基准并做独立回归；不把改变版本字符串当作修复。
