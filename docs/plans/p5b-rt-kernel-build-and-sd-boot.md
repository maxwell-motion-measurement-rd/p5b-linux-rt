# P5B Linux 5.4.0 PREEMPT_RT 编译与首轮 SD 启动包计划

日期：2026-10-27。状态：第 1–7 步主机构建与打包完成；baseline 基本启动和 RT Core0／1／2 三核首次启动已验证。完整 RT 状态、基本读写及已加载模块检查通过；外设功能、实时延迟和 AMP 共存仍待验证。实测见 [baseline 记录](../board/baseline-first-boot-20261027.md)与 [RT 记录](../board/rt-first-boot-20261027.md)。下文保留构建时的操作顺序，当前结果以板端记录为准。

## 执行进度

| 步骤 | 状态与证据 |
| --- | --- |
| 1 | 已完成：原源码工作树干净；补丁两端校验通过；原版启动三件套已逐文件比对并保存在 Ubuntu 的 /home/wang/p5b-rt-5.4.0/deploy/baseline |
| 2 | 已完成：独立 worktree 实际应用 398 个文件，零失败、零模糊匹配；允许完整上下文下的行号偏移；反向严格试贴通过 |
| 3 | 已完成：CONFIG_PREEMPT_RT=y；版本 5.4.0-rt1-xilinx-v2020.2-p5b；显式工具链 sysroot 编译/链接预检通过 |
| 4 | 已完成静态配置：CONFIG_NR_CPUS=3；Linux DTB 删除 CPU3 节点及其符号，PMU IRQ/affinity 限于前三核；bootargs 为 earlycon console=ttyPS0,115200 rdinit=/init rw |
| 5 | 已完成：AArch64 Image 和 62 个匹配模块构建成功，含 4 个外部模块；依赖检查通过；实际 Image 内嵌配置与交付配置一致；保留 3 条非致命编译警告 |
| 6 | 已完成：新 FIT 19,501,100 字节，内核、DTB、initramfs 和 SHA-256 校验通过；原 rootfs 的 1250 个未替换条目保留原数据及 Unix 元数据，62 个模块已更新 |
| 7 | 已完成：中文部署/回退说明、版本清单、配置、构建证据和 ZIP 已生成并通过校验；原源码 HEAD/状态与原启动文件未变 |

额外模块已从原工程缓存源码 xilinx/vcu-modules，固定提交 844d4c4292e08ad8c3f22ac78e9a937395c1db4b 重新构建：allegro、al5e、al5d、dmaproxy。原 rootfs 的 dmaproxy 自动加载配置已保留。

最终 Ubuntu 启动包：/home/wang/p5b-rt-5.4.0/deploy/p5b-rt-sd-20261027.zip，45,463,094 字节。

ZIP SHA-256：a1a684b678e5eb82a4d04cdbbbdf7e5279792cd257f32674c71b33f285f840a7。

内核主构建于北京时间 11:16:33 开始、11:31:22 完成。实际 Image 版本字符串包含 SMP PREEMPT_RT；最终内嵌配置含 CONFIG_PREEMPT_RT=y、CONFIG_NR_CPUS=3。上板实际运行情况仍待验证。

## 目标与已确认范围

在 Ubuntu 虚拟机中准备一个供 P5B 首次部署验证的 RT Linux 启动包：一个 Linux SMP 实例使用 Core0／1／2，Core3 先预留。首轮不加载 Core3 裸机程序；裸机共存、通信和定量实时性验收另设阶段。

工程采用独立 Git worktree 与独立编译输出；SD 卡启动；FIT image.ub 内包含 initramfs；复用现有 BOOT.BIN 和 boot.scr，并保留原版回退包。

本阶段无板验收覆盖编译、文件包结构和版本一致性。实际启动成功、核心分配、驱动可用性及实时延迟均须上板验证，不提前标为完成。

## 固定基线

| 项目 | 值 |
| --- | --- |
| 原工程 | /home/wang/petalinux/ALIENTEK-MP |
| 原内核源码 | /home/wang/petalinux/ALIENTEK-MP/components/yocto/workspace/sources/linux-xlnx |
| 内核 | Xilinx 2020.2 / 5.4.0 |
| 源码提交 | 62ea514294a0c9a80455e51f1f4de36e66e8c546 |
| 补丁仓库提交 | fred-framework/meta-retis / 02995952c2df1819657f2998e6e3a63c0e2aaa63 |
| 补丁文件 | recipes-kernel/linux/files/patch-5.4.3-rt1.patch |
| 补丁字节数 | 822792 |
| 补丁 SHA-256 | 684ad81ec7d25bd4b268ae5ced3c24bc53b3595aea5c528518cdeeb2e8bee26a |

补丁选型与既往严格试贴结论来自[已有记录](https://app.notion.com/p/4069c4372a9581e5a8e4dbbe64a0d585)。本轮只读 SSH 核查已确认源码提交一致、已跟踪文件无修改；实际应用前仍须重新检查状态和补丁完整性。

现有 XSA 的内部元数据声明器件为 xczu4ev-sfvc784-2-i，版本 2020.2，并包含 PL 位流。实际板卡与该硬件导出的匹配关系待拿到板卡核对。

## 工作目录

拟在 Ubuntu 使用以下独立目录；执行时先检查是否已有同名目录，不覆盖已有内容。

```text
/home/wang/p5b-rt-5.4.0/
├── src/             固定提交的内核 worktree
├── build/           内核独立编译输出
├── inputs/          补丁、原配置和设备树输入副本
├── staging/         模块与 rootfs 暂存
├── logs/            校验、补丁、配置与编译日志
└── deploy/
    ├── rt/          新的首轮上板包
    └── baseline/    原版回退候选包
```

worktree 共享原仓库的 Git 对象，源文件和编译输出独立。原工程的配置、images/linux 和已有源码修改保持原状；worktree 注册会更新 Git 的 worktree 管理信息。

## 按顺序执行

### 1. 固化输入与检查环境

- 重新记录 HEAD、完整工作树状态、配置来源和旧启动文件的 SHA-256；区分未跟踪文件与已跟踪变更，不清理原工程。
- 复制现有 BOOT.BIN、boot.scr、image.ub 及必要来源说明到 baseline，逐文件比对哈希。快照生成时状态为“原版、尚未经本次板端验证”；后续实板基本启动已通过，见板端记录。
- Windows 获取固定补丁并核对大小与 SHA-256，再经 SSH 传入独立 inputs；不依赖虚拟机直连外部站点。
- 核对磁盘预算和工具链。当前 VM 为 4 CPU、约 7.8 GiB 内存，根分区约 27 GiB 可用；初始编译并行度取 4，执行时按实际资源调整。
- 已确认 make、宿主 GCC、bc、bison、flex、cpio、gzip、depmod、mkimage、dumpimage、dtc、fdtget 可找到。是否需要补齐 libelf 等开发依赖，由最终配置和宿主工具预检决定。

验收：输入可追溯，回退候选包完整，环境预检结果可查。发现源码变动或输入哈希不匹配时先处理差异，不继续使用失效的试贴结论。

### 2. 创建隔离源码并应用补丁

- 从固定提交创建独立 worktree，记录其初始状态。
- 在新目录重新做严格试贴，再实际应用同一份补丁；保存命令、退出码和日志。
- 审查改动，确认无失败项、模糊匹配或意外遗留的 .rej；保存完整 diff。
- 若出现与既往记录不一致的冲突，定位原因并记录修复，不悄悄改用其他内核或补丁基线。

验收：隔离源码应用成功，修改可审查，原工程源码内容保持原状。

### 3. 迁移板级配置并启用完整 RT

现有构建配置位于：

```text
/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0/linux-xlnx-5.4+git999/.config
```

- 将其复制到独立输出目录，基于补丁后的 Kconfig 更新配置。
- 保留原有 AArch64、ZynqMP、串口、存储、文件系统及板级驱动支持，启用该补丁提供的完整 PREEMPT_RT 选项。
- 核对最终生成配置中的实际 RT 符号及依赖；检查配置更新是否意外移除了驱动或改回非 RT 抢占模式。
- 保留可识别 RT 构建的版本信息，使用构建系统实际生成的 kernelrelease 作为后续模块目录与验证依据，不根据文件名猜测版本。

验收：最终配置明确启用完整 RT，板级支持差异已有审查记录；保存原配置、最终配置与差异。

### 4. 准备三核 Linux 的设备树与启动参数

- 在设备树输入副本中核对 CPU reg / MPIDR 和 PSCI 配置，确保 Core0／1／2 的映射明确。
- 检查本版本 ARM64 的 CPU 枚举逻辑，联合调整 CPU 节点和内核配置，使 Core3 不进入本轮 Linux 可启动的 CPU 集合；不能只将 Core3 从调度任务中隔离就宣称已预留给裸机。
- 核对 cpu-map 及相关引用，编译并反查最终 DTB；保留原版 DTB。
- 统一为选定的 initramfs 启动路径，检查 /init、内核命令行覆盖设置、设备树 chosen.bootargs 和启动脚本，消除旧的 SD 第二分区 rootfs 参数带来的歧义。
- 本轮不预设裸机内存地址、共享内存区域或通信协议；后续 AMP 阶段再核对这些资源。

验收：静态检查支持目标三核映射，最终启动参数和 initramfs 方案一致。实际核心状态仍留待板端证明。

### 5. 独立交叉编译内核与模块

已只读验证可运行的工具链为 GCC 9.2.0、Binutils 2.32.0.20190204。可使用的完整工具前缀是：

```text
/home/wang/petalinux/ALIENTEK-MP/build/tmp/work/zynqmp_generic-xilinx-linux/linux-xlnx/5.4+git999-r0/recipe-sysroot-native/usr/bin/aarch64-xilinx-linux/aarch64-xilinx-linux-
```

- 显式设置 ARCH=arm64、独立 O= 输出目录和完整交叉工具路径，先预检宿主工具及目标工具选择，再构建 Image 和 modules。
- 参考现有 recipe 的工具选择，包括必要时使用 ld.bfd；不直接执行或 source 原工程的 run.do_compile。
- 模块仅安装到 staging，不安装到 Ubuntu 的 /lib/modules。
- 保存完整日志、退出码、kernelrelease、编译器与链接器版本；检查输出架构。

验收：内核和所需模块构建成功，输出为预期 AArch64 产物，所有错误均已解决或阻止进入打包阶段。

### 6. 更新 initramfs 并生成 RT FIT

- 在独立暂存目录保留原 rootfs 用户空间，更新与新 kernelrelease 匹配的模块及依赖信息。
- 排查额外模块及其源码来源；不能将旧内核模块直接当成 RT 新内核模块交付，也不能通过强制加载绕过版本检查。
- 保留 rootfs 的权限、所有权、符号链接及必要设备节点；不能因普通用户解包而丢失部署语义。重新打包后反查归档。
- 参考既有 FIT 的结构，使用明确指向独立输出的 .its，组合新 RT 内核、新 Linux DTB 和更新后的 initramfs。
- 用 dumpimage 等工具核对 FIT 默认配置及三类载荷；对提取或解析得到的组件哈希与输入逐一核对。检查加载地址、镜像尺寸和占用区间。
- 复用现有 BOOT.BIN / boot.scr。分别标注 BOOT.BIN 中的启动阶段 DTB 与 FIT 中的 Linux DTB，核对实际 Linux 使用的是新 DTB。

验收：RT image.ub 内实际包含正确版本的三个组件；模块和内核一致。只替换散放的 Image 或 system.dtb 不作为 FIT 更新成功的证据。

### 7. 交付首轮上板包与说明

```text
deploy/rt/
├── BOOT.BIN
├── boot.scr
├── image.ub
├── SHA256SUMS
├── build-manifest.txt
├── final.config
├── DEPLOY.md
└── ROLLBACK.md
```

另保留构建日志、模块包、Image、Linux DTB、initramfs 和调试符号等可追溯产物。部署说明区分“需要复制到 SD 启动分区的文件”和“构建记录”，避免混用旧、新包。

DEPLOY.md 说明 SD 启动文件布局、板卡匹配检查、串口连接、首次检查命令及预期证据。启动拨码、实际串口和 MMC 编号须依据到手板卡资料核对，不照搬其他开发板设置。不在本轮远程格式化任何 SD 卡或写入板载 Flash。

ROLLBACK.md 说明如何恢复原版三件套，并区分快照生成时状态与后续 baseline 基本启动结果。发现问题时先确定失败发生在固件、U-Boot、内核还是用户空间阶段。

## 无板阶段完成标准

- 固定基线、补丁完整性、实际应用记录及改动可追溯。
- 完整 RT 配置经过最终生成结果核对，内核和所需模块编译成功。
- 三核相关配置与最终 DTB 静态检查通过；尚不宣称实际分核成功。
- FIT 默认配置引用正确的 RT 内核、Linux DTB 和 initramfs，模块与 kernelrelease 一致。
- RT 包和原版回退候选包分别保存，哈希清单、复现步骤和部署说明完整。
- 明确列出仍须上板验证的事项，不将“准备好文件包”记为“板端已跑通”。

## 拿到板卡后的验证顺序

1. 核对板卡型号、硬件版本与 XSA/BSP 的匹配，确认 SD 启动方式和串口。保留原有存储内容。
2. 保存原版基线的启动结果，再测试 RT 包，保留完整串口日志，以区分固件与新内核问题。
3. 核对实际运行内核版本和 RT 配置，确认 Core0／1／2 的标识、CPU 可用集合与在线状态；确认 Core3 未被 Linux 使用。
4. 检查串口、SD、网络及本次启动所需驱动和模块。PL 功能按实际硬件设计分别验证。
5. 记录实时延迟初测条件和结果；量化阈值、负载与正式实时性验收另行确定。
6. 进入下一阶段时再定义并验证 Core3 裸机启动、内存／中断／外设归属和 Linux／裸机通信。

## 参考

- [项目补丁选型记录](https://app.notion.com/p/4069c4372a9581e5a8e4dbbe64a0d585)
- [项目部署主线](https://app.notion.com/p/3fb9c4372a9581d69079c2bb8b1b54f7)
- [PetaLinux 2020.2 SD 启动步骤](https://docs.amd.com/r/2020.2-English/ug1144-petalinux-tools-reference-guide/Steps-to-Boot-a-PetaLinux-Image-on-Hardware-with-SD-Card)
- [AMD 2020.2 预编译镜像布局](https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/1065451521/2020.2%2BRelease)
- [Linux initramfs 文档](https://docs.kernel.org/filesystems/ramfs-rootfs-initramfs.html)
