# P5B Linux 5.4.0 PREEMPT_RT 构建记录

本仓库记录 P5B RT 内核的移植和构建过程，保存执行计划、技术决策、构建脚本、补丁和配置。内核修改可在固定基线上通过 Git 补丁重放，完整的 Linux 提交历史见上游仓库。

## 当前状态

截至 2026-10-27，已在 Ubuntu 上完成补丁集成、AArch64 内核和 62 个模块的构建，并生成首轮 SD 启动包。板端启动、驱动功能、三核实际运行和实时延迟均尚未验证。

- 厂商基线：Xilinx 2020.2 / Linux 5.4.0。
- 基线提交：`62ea514294a0c9a80455e51f1f4de36e66e8c546`。
- RT 补丁来源：`fred-framework/meta-retis`，提交 `02995952c2df1819657f2998e6e3a63c0e2aaa63`。
- 原始补丁：`work/inputs/patch-5.4.3-rt1.patch`，822792 字节。
- 原始补丁 SHA-256：`684ad81ec7d25bd4b268ae5ced3c24bc53b3595aea5c528518cdeeb2e8bee26a`。
- 构建版本：`5.4.0-rt1-xilinx-v2020.2-p5b`。
- 配置：`CONFIG_PREEMPT_RT=y`、`CONFIG_SMP=y`、`CONFIG_NR_CPUS=3`。
- 本轮仅预留 Core3，未加入裸机程序，也未验证 AMP 共存。

## 目录

- `docs/plans/`：执行计划及完成进度。
- `docs/adr/`：厂商基线和核心分工的决策记录。
- `docs/build/`：交付清单、静态验证结果和 Git 提交记录。
- `configs/`：原始配置、最终配置、Linux DTS 和 FIT ITS。
- `patches/`：RT 源码提交导出的 Git 补丁及三核设备树差异。
- `patches/p5b-rt-commit.bundle`：备份 RT 内核新增提交的 Git 对象，恢复前需取得上述厂商基线提交。
- `work/scripts/`：实际使用的构建、打包和验证脚本。
- `work/inputs/`：固定来源的原始 RT 补丁。
- `work/artifacts/`：部署说明、回退说明和 ZIP 校验值。
- `GLOSSARY.md`：项目术语。

## 复现边界

先阅读 `docs/plans/p5b-rt-kernel-build-and-sd-boot.md`。脚本使用的是本次 Ubuntu 环境中的源工程、工具链、缓存和输出路径，换到其他机器时需先核对并统一调整。部分阶段脚本依赖上一步生成的输入和完成标记，不能直接在已完成的目录中重新初始化或重复打补丁。

应用 RT 补丁时，选择 `work/inputs/` 中的原始补丁，或重放 `patches/` 中等价的 Git 提交补丁，两种方式不要重复使用。构建采用 GCC 9.2.0 的 AArch64 工具链，需显式指定 sysroot 和 ld.bfd，并将编译输出与源码目录分开。

RT 修改已提交到 Ubuntu 的 `p5b-rt-5.4.0` 分支，提交为 `e4cc2d02d270570055fe2b46ca2eb17c21938504`，父提交是上述厂商基线。若要恢复完全相同的提交，使用 bundle，具体步骤见 `docs/build/kernel-git-backup.md`。

复现前需准备匹配的原工程输入：完整 BSP、原 rootfs、BOOT.BIN、位流和工具链均未包含在本仓库中，构建二进制也另行保存。脚本和补丁沿用各自来源的许可声明，本仓库不改变原许可。

## 首轮部署

部署步骤见 `work/artifacts/P5B-DEPLOY.md`，回退步骤见 `work/artifacts/P5B-ROLLBACK.md`。启动包为 `p5b-rt-sd-20261027.zip`，大小为 45,463,094 字节，SHA-256 为：

```text
a1a684b678e5eb82a4d04cdbbbdf7e5279792cd257f32674c71b33f285f840a7
```

ZIP 和其他大体积构建产物未纳入 Git；SSH 私钥、连接配置及本地执行检查点也已排除。
