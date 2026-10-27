---
status: accepted
---

# 保留厂商内核，采用已记录的 RT 移植基线

保留 Xilinx 2020.2 的 Linux 5.4.0 源码和现有板级驱动，不为匹配补丁直接升级或降级内核。固定采用 RETIS 提交中的 patch-5.4.3-rt1.patch 作为移植输入；该补丁在下列厂商源码提交上通过零失败、零 fuzz 应用和反向检查，随后完成内核、模块构建及本轮 RT 三核启动。

这保留了板级支持，也意味着后续必须验证厂商修改与 RT 行为能否共同工作。只读试贴不构成编译、启动或实时性验收；如实际源码状态改变，需重新核对适用性。

## 为什么不使用 Linux 4.9 的 RT 补丁

PREEMPT_RT 是对特定内核源码的修改，涉及锁、中断、调度、定时器和架构实现，不是独立于内核版本的驱动包。4.9 与 5.4 的接口和实现有差异，4.9 补丁不能直接作为当前 5.4.0 厂商内核的通用补丁。强行应用、忽略冲突或只修到能编译，不能证明 RT 语义正确。

本工程已经使用 PetaLinux／Xilinx 2020.2 和厂商 5.4.0 的 BSP、驱动、设备树及启动固件。选择 4.9 应当作为另一条完整内核／BSP 适配路线，同时重新核对硬件支持、工具链、固件与驱动并做板端回归，不是单独替换 RT 补丁。本轮没有执行 4.9 降级或移植，没有对某个具体 4.9 补丁做失败试贴，也不以“4.9 性能更差”为选型理由。

5.4.3-rt1 的文件名同样不保证任意 5.4.0 厂商内核适用。本次依据是固定来源和厂商提交上的实际应用、构建及上板证据，内核主体仍为厂商 5.4.0；实时延迟和完整外设行为尚未验收。不能把这一记录泛化为“PetaLinux 2020.2 完全不支持 RT”。

官方 RT 补丁按内核系列分别归档：[4.9](https://www.kernel.org/pub/linux/kernel/projects/rt/4.9/)、[5.4](https://www.kernel.org/pub/linux/kernel/projects/rt/5.4/)。Linux Foundation 的[安装说明](https://wiki.linuxfoundation.org/realtime/documentation/howto/applications/preemptrt_setup)也要求选择对应的内核源码与 RT 补丁。上述资料说明版本匹配原则；本次厂商移植是否成功由仓库中的构建证据和板端日志支持。

源码提交：62ea514294a0c9a80455e51f1f4de36e66e8c546。

补丁仓库：fred-framework/meta-retis，提交 02995952c2df1819657f2998e6e3a63c0e2aaa63，路径 recipes-kernel/linux/files/patch-5.4.3-rt1.patch。

补丁 SHA-256：684ad81ec7d25bd4b268ae5ced3c24bc53b3595aea5c528518cdeeb2e8bee26a。

固定补丁来源：[meta-retis 原文件](https://github.com/fred-framework/meta-retis/blob/02995952c2df1819657f2998e6e3a63c0e2aaa63/recipes-kernel/linux/files/patch-5.4.3-rt1.patch)。原文件在 work/inputs 中，等价内核提交补丁和 bundle 在 patches 中，选择一种重放方式，不能重复应用。
