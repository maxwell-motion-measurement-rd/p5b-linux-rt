# P5 RT Linux：串口登录自动加载 ble.sh

生成日期：2026-10-28。新版镜像已完成主机侧打包和静态校验，尚未进行新版 image.ub 的首次上板启动验证。此前临时 ble.sh 会话的高亮效果已在 P5 板端确认正常，两者的验证状态分开记录。

## 本包内容

```text
rt-blesh/image.ub       新版：加入 ble.sh 和串口自动加载
rt-original/image.ub    原 RT 镜像，用于回退
README.md               本说明
SHA256SUMS              包内文件校验
evidence/               镜像、rootfs、登录流程校验结果
source/                 本次新增配置、生成脚本及 FIT ITS
```

新版仅更新 initramfs。原内核、Linux 三核设备树和 62 个模块保留原字节，原 initramfs 全部旧条目的数据、权限、所有者及其他归档元数据均保留。没有重新编译内核，没有修改 fstab、账号 Shell、/bin/sh、/etc/profile、BOOT.BIN 或 boot.scr。

新增路径：

```text
/opt/p5-blesh/blesh/ble.sh
/opt/p5-blesh/start.sh
/opt/p5-blesh/bashrc
/opt/p5-blesh/manifest.json
/etc/profile.d/90-p5-blesh.sh
```

## 自动加载行为

登录后，现有 /etc/profile 会读取新增的 profile.d 脚本。仅交互式 /dev/ttyPS0 串口登录会启动独立高亮 Bash；系统启动脚本、非交互命令及其他终端不会因此自动进入 ble.sh。插件不可用时保留普通登录 Shell。

交互配置将 vt100／vt102 等终端声明适配为 xterm，ls 等外部命令与 cd 等内置命令为蓝色加粗，关闭自动建议。LC_ALL=C 仅用于子 Shell，不保存 Shell 历史。缓存继续放在 /tmp，首轮启动高亮时可能重新生成缓存；自动加载不会消除串口交互卡顿。

## 部署到当前已验证的 SD 卡

1. 保存当前串口输出，在板端执行 sync、poweroff，等待关机后关闭电源。
2. 将 SD 卡接到主机。先把卡上现有 image.ub 另存为回退文件。
3. 仅把本包 rt-blesh/image.ub 复制到 SD 启动分区根目录，覆盖原 image.ub。不要复制外层目录，不用替换 BOOT.BIN、boot.scr，不用格式化卡或改写板载 Flash。
4. 安全弹出卡，断电插回，保持现有 SD 启动拨码。用 115200 8N1 串口保存新一轮完整日志。
5. 进入串口登录后，应自动显示 P5 Bash + ble.sh loaded，不再需要手动解压试用包或输入启动命令。

Windows 可用 Get-FileHash 对照 SHA256SUMS；Linux 主机可在解压包目录执行 sha256sum -c SHA256SUMS。

## 首次启动验收

在板端逐行执行：

```sh
uname -r
cat /sys/kernel/realtime
cat /sys/devices/system/cpu/online
cat /proc/cmdline
echo "$BASH_VERSION"
echo "$BLE_VERSION"
echo "$TERM"
ble-face command_file command_builtin
ls /opt/p5-blesh/blesh/ble.sh
```

预期：

```text
内核：5.4.0-rt1-xilinx-v2020.2-p5b
realtime：1
CPU online：0-2
bootargs：earlycon console=ttyPS0,115200 rdinit=/init rw
Bash：5.0.7(1)-release
ble.sh：0.4.0-devel4+cb9c2c3
TERM：xterm
command_file：fg=blue,bold
command_builtin：fg=blue,bold
```

观察输入 ls、cd 时的颜色，并检查退格、方向键、Tab、Ctrl-C、粘贴与退出。重新启动一次，确认文件仍可由镜像恢复、串口登录仍自动加载。初次自动加载和重启验证通过前，不将新版镜像标为已完成板端验收。

## 退出、临时禁用与回退

执行 exit 退出高亮子 Shell，返回原登录 Shell。当前登录会话不会立即强制重开 ble.sh，便于排障。

若需要当前这次开机后续登录不再自动加载，在普通 Shell 执行：

```sh
touch /etc/p5-blesh.disabled
```

这是内存根文件系统中的临时标记，重启后消失；启动参数包含 p5_blesh=off 时，登录钩子也会跳过自动加载。添加启动参数需按实际 U-Boot／FIT 启动流程处理，本包没有自动修改它。

若新版无法正常使用，保存故障日志，正常关机、断电后，用 rt-original/image.ub 恢复 SD 根目录的 image.ub。若系统已无法响应，先保留当前输出，确认没有烧写操作，再断电取卡回退。

## 摘要和来源

新版 image.ub：20,141,540 字节，SHA-256：

```text
7163089a1793cc3f5b0fb1d174e8371567fd493ff7e7ece01cd0be622f928df0
```

原 RT image.ub SHA-256：

```text
f7c224640ad30359a731a5492f06769b4f081496c88fbe273022c48fd2789484
```

ble.sh 固定提交：cb9c2c37678becc70f38adca57d0b872a7259448；contrib：d2109203480a7dfe1dead5f5f8f9f15a9146c90d。上游：https://github.com/akinomyoga/ble.sh，许可文件保留在镜像内。

Ubuntu 构建目录：/home/wang/p5-rt-blesh-20261028。生成原始输出、配置和日志均保留在该独立目录。主机测试覆盖归档保留、FIT 摘要、非交互 Shell 不被接管，以及模拟串口登录启动子 Bash、退出返回父 Shell；这些测试不能代替实际新镜像上板。


## 交付包校验

文件名：p5-rt-blesh-autostart-20261028.zip，39,438,262 字节。

```text
81ead14f1b8c1f756a5074abb29c70d375857d3348e16b81356cb0a967b4ad23
```

Windows 输出目录：

```text
C:\Users\13931\Documents\Codex\2026-10-27\p5b-linux-arm0-1-2-linux\outputs
```

Ubuntu 文件：

```text
/home/wang/p5-rt-blesh-20261028/p5-rt-blesh-autostart-20261028.zip
/home/wang/p5-rt-blesh-20261028/output/image.ub
```

主机侧已检查 ZIP CRC、包内文件读回及摘要；清理后再次核对新版 image.ub 和 ZIP，摘要未变。构建清单与模拟登录检查见 [构建清单](../../configs/blesh/build-manifest.json)、[登录检查](../../configs/blesh/login-validation.json)，登录钩子见 [90-p5-blesh.sh](../../tools/blesh/90-p5-blesh.sh)。


## 文件保留与清理记录

2026-10-28 已删除 Windows 和 Ubuntu 中的旧手动试用压缩包、校验文件、说明及临时脚本，并删除 Ubuntu 的旧目录 /home/wang/p5-blesh-trial-20261028，包含其源码和运行文件。板上文件未清理；原 RT 工程、新自动加载镜像、原 RT 回退镜像及新方案共用的配置保留。

旧手动版本的板端显示验证作为历史结果保留，但原本地试用包已不再提供。旧构建目录中保存的生成脚本引用已删除的试用运行目录，不能直接原样重跑；重建前需从上游固定提交重新构建 ble.sh，准备运行目录并调整脚本输入路径。源码版本见本文末尾及早期试用记录。

自动加载包目前保存在本地，尚未作为 GitHub Release 附件发布。公开的 board-boot-20261027 Release 仍是原 baseline／RT 启动包，不含自动加载功能。
