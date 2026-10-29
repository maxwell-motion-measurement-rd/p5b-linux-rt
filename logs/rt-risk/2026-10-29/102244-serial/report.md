# P5 原始 RT 风险评估：本轮执行结果

执行日期：2026-10-29，Asia/Shanghai。运行ID：102244-serial。结果：**原始RT基准核对与资源盘点完成；测试工具准备受阻，未执行实时延迟或压力测试。**

## 分步结果

| 阶段 | 操作 | 结果 |
| --- | --- | --- |
| S02 串口 | COM3、115200、8N1、无流控，先发送回车确认提示符 | 成功进入已有root Linux会话，原工作目录/sys/class/leds；每次操作后释放串口 |
| S02 基准 | 核对SD三件套、配置、Shell、RT与CPU | 与保存基准一致，详见下表 |
| S03 资源盘点 | 读取当前设备树、驱动、总线、网口、存储、IRQ与频率 | 完成；具体可见性及限制见hardware-inventory.md |
| S03 RTC／温度 | 只读两次RTC，读取AMS IIO | RTC约2秒递增；PS温度单次约59.56℃；PL通道raw=0不作有效值 |
| S04 工具检查 | command -v及BusyBox applet检查 | cyclictest、stress-ng、stress、taskset、chrt、timeout均缺失 |
| S04 构建主机 | 检查并启动既有Ubuntu虚拟机，重试SSH | VM已启动；SSH可达，但原私钥文件读取被拒绝，认证失败，无法检查／使用原工具链 |
| S05–S07 | 冒烟、分项和联合负载 | 未启动；不能报告延迟、抖动或压力稳定性结果 |

## 基准证据

```text
kernelrelease = 5.4.0-rt1-xilinx-v2020.2-p5b
realtime = 1
possible / present / online = 0-2 / 0-2 / 0-2
bootargs = earlycon console=ttyPS0,115200 rdinit=/init rw
BOOT.BIN = 1459d13f776071430d11c3d1476cd0a1bbfd1476609617a72e762602675d9b9b
boot.scr = 96a830a29dd3b3ba7063e6e916ead3b4df490c96c062a1854c41bd20fd4ef229
image.ub = f7c224640ad30359a731a5492f06769b4f081496c88fbe273022c48fd2789484
embedded config = a1f4db68bbbc5c27e3da8819ad02b7741eeebe13f28545c4b77308871f0438d0
/bin/bash.bash = f15da987dfa4026cde4c83df9437b1b5d994747cd6266bb6976b6c3c886a946a
BLE_VERSION = unset
```

以上摘要来自当前挂载的SD文件及运行中的内嵌配置／Shell。/opt/p5-blesh及其profile钩子不存在。本轮未重新启动，未捕获完整U-Boot日志，也没有对运行中整个rootfs逐文件重验；这些证据支持当前环境与原始RT基准一致。

原参数保持：userspace governor、scaling_cur_freq采样1199999kHz，RT period=1000000μs、runtime=950000μs。未修改CPU/IRQ亲和性、频率、启动参数、内核、设备树或存储内容；未加载ble.sh、启动Core3裸机或操作电机。

## 硬件访问问题的实际发现

- 按键：当前DT有gpio-keys，但内核未启用INPUT_KEYBOARD，且没有注册Input设备。这是驱动配置缺口，不能仅归因于DT遗漏。
- PS SPI0／1：运行中的DT节点均disabled，SPI_SPIDEV也未启用。
- EEPROM：I²C 0-0050节点与at24驱动均存在，但没有driver链接／eeprom文件；需进一步定位匹配或probe路径。本轮未尝试强制绑定、总线探测或写入。
- eth0没有物理链路，eth1 down，无已确认网络对端。网络压力测试缺前提。
- USB仅识别Hub，没有专用测试U盘。eMMC FAT仍存在未正常卸载警告，未进行写入测试或修复。
- VCU仍在devices_deferred中。旧视频、时钟、SPI NOR等错误也见于本轮dmesg；没有因这些旧错误直接认定RT移植失败。

保存的dmesg未发现Kernel panic、Oops、Call trace或BUG报告；这只覆盖本次检查时已保留的日志，不代表长期稳定性通过。

## 当前阻塞与续接

原构建虚拟机：D:/virtual_machines/Ubuntu_64/Ubuntu 64 位.vmx。已通过vmrun以nogui方式启动，后续确认进程与电源状态正常；本轮没有关停它。

默认隔离环境中连接超时；在可访问虚拟机的执行上下文中，SSH返回以下错误摘要：

```text
Load key ".../work/ssh/p5b_vm_ed25519": Permission denied
wang@192.168.127.128: Permission denied (publickey,password).
```

因此需要恢复现有p5b-vm SSH入口对密钥的合法读取／认证，或提供另一条已授权可用的构建主机访问方式。本轮未修改私钥ACL、复制凭据或索取密码，也没有编译、安装或传输工具到板端。

后续从S04继续：工具链可用后，构建／核验ARM64工具，作为临时载荷部署到/tmp，核对帮助和退出方式，明确运行参数，再执行T00。运行网络测试前需要实际链路和对端；存储压力测试需要确认健康的测试介质。此次没有遗留板端负载进程。

## 结果文件

- 00-console-probe.txt：提示符确认。
- 01-identity.txt、02-baseline-hashes.txt：版本、摘要、Shell、内存、进程、频率、IRQ。
- 03-inventory.txt、05-resources.txt、06-hardware-detail.txt、07-deferred.txt：设备和工具盘点。
- 04-dmesg.txt：完整读取的本轮dmesg。
- hardware-inventory.md：资源表。
- manifest.json、SHA256SUMS：本次状态及证据摘要。

板端RTC日期仍为2026-10-23，未校时；测试日期以主机Asia/Shanghai日期为准。原始串口文本保留回显／控制字符，未润色。根目录中的状态JSON已更新，未执行项目保持planned或blocked，没有用本次只读检查替代实时测试。
