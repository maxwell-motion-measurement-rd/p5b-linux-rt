# RT 内核 Git 提交备份

2026-10-27，将已构建的 RT 内核源码修改提交到独立分支，保留原工程的 devtool 分支。

- 分支：`p5b-rt-5.4.0`。
- RT 提交：`e4cc2d02d270570055fe2b46ca2eb17c21938504`。
- 父提交：`62ea514294a0c9a80455e51f1f4de36e66e8c546`。
- 修改文件数：398，包含 RT 新增文件。
- 提交后 RT 工作区干净；本次未重新编译，也未修改现有构建产物。

## 备份内容

`patches/0001-apply-preempt-rt-to-xilinx-5.4.0.patch` 是该提交导出的 format-patch，可在匹配的厂商基线上用 git am 重放。已经执行 git apply --check 确认该补丁可应用到原始基线。它和 work/inputs 下的原始 RT 补丁是两种替代应用方式，不要重复应用。

`patches/p5b-rt-commit.bundle` 保存了新增提交所需的 Git 对象，以及指向上述 RT 提交的分支引用。它要求接收方已有父提交，不能直接当成包含完整 Linux 历史的独立仓库克隆。

SHA-256：

```text
eab6752a44a0a8aa374ca32aafbdd46df0ff551bb0212f284bb08408b86a09ca  0001-apply-preempt-rt-to-xilinx-5.4.0.patch
e6ad673e4869b5278e1d2cb241b276140d3f8ac010205086295fdc137f83a0c5  p5b-rt-commit.bundle
```

## 恢复相同的内核提交

以下在已取得厂商父提交的内核仓库中执行。路径为示例，分支和新目录不得覆盖已有工作：

```bash
git cat-file -e 62ea514294a0c9a80455e51f1f4de36e66e8c546^{commit}
git bundle verify /path/to/p5b-rt-commit.bundle
git fetch /path/to/p5b-rt-commit.bundle \
    refs/heads/p5b-rt-5.4.0:refs/heads/p5b-rt-5.4.0
git rev-parse p5b-rt-5.4.0
git worktree add /path/to/new-rt-src p5b-rt-5.4.0
```

rev-parse 的结果应为上述 e4cc2d02d270570055fe2b46ca2eb17c21938504。bundle 已在含父提交的原内核仓库中通过 verify 检查。

本记录保存源码提交，不构成板端启动或实时性验证。
