---
status: accepted
---

# 保留厂商内核，采用已记录的 RT 移植基线

依据 2026-10-27 的[补丁选型与只读试贴记录](https://app.notion.com/p/4069c4372a9581e5a8e4dbbe64a0d585)，保留 Xilinx 2020.2 的 Linux 5.4.0 源码和现有板级驱动，不为匹配补丁直接升级内核。该记录将 RETIS 固定提交中的 patch-5.4.3-rt1.patch 选为移植基线，因为它已在记录所指的厂商源码上通过严格的只读试贴。

这保留了板级支持，也意味着后续必须验证厂商修改与 RT 行为能否共同工作。只读试贴不构成编译、启动或实时性验收；如实际源码状态改变，需重新核对适用性。

源码提交：62ea514294a0c9a80455e51f1f4de36e66e8c546。

补丁仓库：fred-framework/meta-retis，提交 02995952c2df1819657f2998e6e3a63c0e2aaa63，路径 recipes-kernel/linux/files/patch-5.4.3-rt1.patch。

补丁 SHA-256：684ad81ec7d25bd4b268ae5ced3c24bc53b3595aea5c528518cdeeb2e8bee26a。
