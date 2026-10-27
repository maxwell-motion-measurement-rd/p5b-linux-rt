# P5B Linux 5.4.0 PREEMPT_RT 构建记录

本仓库保存 P5B RT 内核移植的计划、决策、构建脚本、固定补丁及配置记录。完整 Linux 内核历史保留在上游仓库，内核修改通过固定基线和 Git 补丁重放。

## 当前状态

2026-10-27 已完成 Ubuntu 上的补丁集成、AArch64 内核及 62 个模块构建，并生成首轮 SD 启动包。尚未进行板端启动、驱动功能、三核实际运行或实时延迟验证。

- 厂商基线：Xilinx 2020.2 / Linux 5.4.0。
- 基线提交：`62ea514294a0c9a80455e51f1f4de36e66e8c546`。
- RT 补丁来源：`fred-framework/meta-retis`，提交 `02995952c2df1819657f2998e6e3a63c0e2aaa63`。
- 原始补丁：`work/inputs/patch-5.4.3-rt1.patch`，822792 字节。
- 原始补丁 SHA-256：`684ad81ec7d25bd4b268ae5ced3c24bc53b3595aea5c528518cdeeb2e8bee26a`。
- 构建版本：`5.4.0-rt1-xilinx-v2020.2-p5b`。
- 配置：`CONFIG_PREEMPT_RT=y`、`CONFIG_SMP=y`、`CONFIG_NR_CPUS=3`。
- 本轮只预留 Core3，不包含裸机程序或 AMP 共存验证。

## 目录

- `docs/plans/`：执行计划及完成进度。
- `docs/adr/`：厂商基线和核心分工的决策记录。
- `docs/build/`：交付清单、静态验证结果及 Git 追溯记录。
- `configs/`：原配置、最终配置、Linux DTS 和 FIT ITS。
- `patches/`：RT 源码提交导出的 Git 补丁及三核设备树差异。
- `patches/p5b-rt-commit.bundle`：RT 内核新增提交的 Git 对象备份；恢复时需要先取得上述厂商基线提交。
- `work/scripts/`：实际使用的构建、打包和验证脚本。
- `work/inputs/`：固定来源的原始 RT 补丁。
- `work/artifacts/`：部署说明、回退说明和 ZIP 校验值。
- `GLOSSARY.md`：项目术语。

## 复现边界

先阅读 `docs/plans/p5b-rt-kernel-build-and-sd-boot.md`。脚本中的源工程、工具链、缓存和输出路径来自本次 Ubuntu 环境；在其他机器上使用前，需要核对并统一调整路径。部分阶段脚本依赖前一步生成的输入和完成标记，不能在已完成目录上直接重复初始化或打补丁。

只选择一种 RT 补丁应用方式：使用 `work/inputs/` 的原始补丁，或重放 `patches/` 中等价的 Git 提交补丁；不要重复应用两者。使用 GCC 9.2.0 的 AArch64 工具链，显式指定 sysroot 和 ld.bfd，编译输出与源码目录分离。

本次 RT 修改已提交到 Ubuntu 的 `p5b-rt-5.4.0` 分支，提交为 `e4cc2d02d270570055fe2b46ca2eb17c21938504`，父提交是上述厂商基线。需要恢复完全相同的提交时，使用 bundle；恢复说明见 `docs/build/kernel-git-backup.md`。

本仓库不包含原工程完整 BSP、原 rootfs、BOOT.BIN、位流、工具链或构建二进制。复现时需要准备匹配的原工程输入。脚本和补丁沿用各自来源中的许可声明，本仓库不改变原许可。

## 首轮部署

部署说明见 `work/artifacts/P5B-DEPLOY.md`，回退说明见 `work/artifacts/P5B-ROLLBACK.md`。启动包为 `p5b-rt-sd-20261027.zip`，45,463,094 字节；SHA-256 为：

```text
a1a684b678e5eb82a4d04cdbbbdf7e5279792cd257f32674c71b33f285f840a7
```

ZIP 及其他大体积构建产物未纳入 Git。SSH 私钥、连接配置和本地执行检查点也不纳入 Git。
