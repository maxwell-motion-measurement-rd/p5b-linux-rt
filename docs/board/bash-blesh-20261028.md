# P5 串口 Bash 语法高亮配置与验证

> 当前状态（2026-10-28）：本文保留早期手动试用的操作和验证。旧本地试用包、源码及运行目录已清理；新自动加载 image.ub 已生成并通过主机侧检查，尚未上板验证。当前部署、回退、校验值和文件保留情况见 [自动加载镜像说明](bash-blesh-autostart-20261028.md)。以下手动命令仅供追溯。

记录日期：2026-10-28。本次在 P5 实板的 COM3 串口上启用 Bash + ble.sh，终端显示效果已经人工确认正常。这是交互式调试环境的改动，没有重新编译内核，也没有修改已验证的 RT image.ub、系统默认登录 Shell 或 /etc/profile。

## 环境与原因

| 项目 | 实测结果 |
| --- | --- |
| 串口 | COM3，115200，8N1，无流控 |
| 登录 Shell | 以 -sh 名称运行的 Bash，/bin/sh 与当前进程均指向 /bin/bash.bash |
| 板端 Bash | 5.0.7(1)-release |
| ble.sh | 0.4.0-devel4+cb9c2c3 |
| 源码提交 | cb9c2c37678becc70f38adca57d0b872a7259448 |
| contrib 提交 | d2109203480a7dfe1dead5f5f8f9f15a9146c90d |

最初普通 ls 和命令输入没有高亮，需要区分三个功能：ls --color 控制目录列表颜色，MobaXterm 规则匹配日志关键词，ble.sh 负责输入时的 Shell 语法高亮。目录颜色和 ANSI 测试正常，不代表 ble.sh 已加载。

直接串口检查发现 BLE_VERSION 未设置，当前会话尚未加载插件。试用包已解压在 /tmp/p5-blesh-trial，但需要显式运行启动器。原 TERM=vt102，随后使用 TERM=xterm 启动试用 Bash，插件报告 8 色能力。仅修改 TERM 不是充分的成功判据，最终以实际输入显示确认。

## 启动与配置

试用包原文件为 p5-blesh-trial-20261028.tar.gz，663139 字节，SHA-256：

```text
f97646060f1a21aa89fd58e51e6422a8d1e256d03da34d0c9f878870d540b17e
```

该原包保持最初字节，不包含后续手工配色。已持有原包时，在板端执行：

```sh
tar -xzf /media/sd-mmcblk1p1/p5-blesh-trial-20261028.tar.gz -C /tmp
TERM=xterm /tmp/p5-blesh-trial/start.sh
```

SD 挂载路径以 mount 实际输出为准。MobaXterm 的 Serial 会话能显示 xterm 风格 ANSI 控制序列；这里的 TERM 设置仅传给试用 Shell，不代表改动串口波特率。

进入试用 Bash 后设置命令配色：

```bash
ble-face command_file=fg=blue,bold command_builtin=fg=blue,bold
```

command_file 对应 ls 等外部命令，command_builtin 对应 cd 等内置命令。ble-face 使用 face=value 形式，不能写成两个分离参数 command_file fg=blue,bold。

为了后续启动可以直接复用，本仓库另存 [start.sh](../../tools/blesh/start.sh) 和 [bashrc](../../tools/blesh/bashrc)。bashrc 包含 vt102 到 xterm 的试用适配及上述配色，自动建议关闭，不保存历史；先加载插件、设置颜色，再附加行编辑器。它们是本次成功设置的整理版本，已经做语法检查，未另行在板端替换当前正在运行的会话。原包及原 RT Release 均不因此改写。

## 复现构建

ble.sh 主体是 Bash 脚本，不需要把 Ubuntu x86 可执行文件复制到 ARM 板。Ubuntu 需要 Bash、Git、GNU make 和 gawk；运行时还依赖板端的 awk、sed、grep、stty 等工具，本轮已对 RT initramfs 检查主要工具是否存在。

在 Ubuntu 上，以本仓库克隆路径设置 REPO；使用一个不存在的新输出目录：

```bash
set -euo pipefail
REPO=/path/to/p5b-linux-rt
BLE_WORK=/path/to/new-blesh-work
test ! -e "$BLE_WORK"
mkdir -p "$BLE_WORK/payload/p5-blesh-trial"
git clone https://github.com/akinomyoga/ble.sh.git "$BLE_WORK/source"
git -C "$BLE_WORK/source" checkout --detach cb9c2c37678becc70f38adca57d0b872a7259448
git -C "$BLE_WORK/source" submodule update --init --recursive
make -C "$BLE_WORK/source" -j2
make -C "$BLE_WORK/source" install \
  INSDIR="$BLE_WORK/payload/p5-blesh-trial/blesh" USE_DOC=no
cp "$REPO/tools/blesh/start.sh" "$BLE_WORK/payload/p5-blesh-trial/"
cp "$REPO/tools/blesh/bashrc" "$BLE_WORK/payload/p5-blesh-trial/"
chmod 755 "$BLE_WORK/payload/p5-blesh-trial/start.sh"
bash -n "$BLE_WORK/payload/p5-blesh-trial/bashrc"
sh -n "$BLE_WORK/payload/p5-blesh-trial/start.sh"
tar -czf "$BLE_WORK/p5-blesh-configured.tar.gz" -C "$BLE_WORK/payload" p5-blesh-trial
```

将新生成的包复制到 SD 后，用它自己的文件名解压，再运行 start.sh。新包与最初试用包的摘要不同，应分别记录，不套用上面的原包 SHA-256。项目来源和许可见 [ble.sh](https://github.com/akinomyoga/ble.sh)，安装目录内保留上游许可。

## 验证结果与范围

板端检查命令：

```bash
echo "$BASH_VERSION"
echo "$BLE_VERSION"
echo "$TERM"
ble-face command_file command_builtin
```

本次直接串口采样得到：

```text
B=0.4.0-devel4+cb9c2c3 T=xterm C=8
ble-face command_file=fg=blue,bold
ble-face command_builtin=fg=blue,bold
```

这里的 C 为 ble.sh 内部报告的终端颜色数量。以上是检查输出摘录，不是完整逐字节串口日志。串口释放后，在 MobaXterm 中重新连接，输入命令的高亮效果已人工确认正常；没有将这一反馈扩写为全部快捷键、粘贴场景或所有终端兼容性测试通过。

## 退出与持久化边界

```sh
exit
```

退出后回到原来的串口 Shell。试用文件和缓存位于 /tmp，重启后消失；再次使用需要重新解压并启动。本轮未把 ble.sh 纳入 initramfs，未修改 /bin/sh、账号登录设置、fstab 或现有启动三件套，也未开展新的 RT 性能测试。

若 MobaXterm 的关键词规则与 Shell 颜色叠加，可在观察 ble.sh 时关闭关键词规则。MobaXterm 规则只匹配文字，不能代替 Shell 语法高亮。
