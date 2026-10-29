# 板端资源盘点

执行日期：2026-10-29，主机时区Asia/Shanghai；板上RTC为2026-10-23，未修改时钟。接口：COM3，115200、8N1、无流控。以下来自本轮串口只读检查。

| 对象 | 观察结果 | 当前结论 |
| --- | --- | --- |
| 内核与RT | 5.4.0-rt1-xilinx-v2020.2-p5b；realtime=1 | 符合原始RT基准版本和标志 |
| CPU | possible/present/online均0-2 | Linux使用3核；不证明Core3裸机或AMP共存 |
| SD启动文件 | BOOT.BIN、boot.scr、image.ub摘要与保存基准相同 | 本次挂载SD上的三件套身份匹配；未捕获本次完整U-Boot启动过程 |
| 配置／Shell | 内嵌配置、/bin/bash.bash摘要匹配；BLE_VERSION未设置，插件路径不存在 | 与无ble.sh的原始环境一致 |
| CPU频率 | userspace，scaling_cur_freq采样1199999kHz | 当前约1.2GHz；未调整governor或频率 |
| RT预算 | period=1000000μs，runtime=950000μs | 保留原值 |
| LED | ps_led0/1、pl_led0/1及MMC LED类节点存在 | 已注册；本次未切换亮灭 |
| RTC | 19:45:28到19:45:30，间隔sleep 2 | 硬件时钟可读且走时；未校时／测断电保持 |
| GPIO | /dev/gpiochip0–6 | 控制器接口已注册；未导出或改变引脚 |
| 板载按键 | 生效设备树有gpio-keys；CONFIG_INPUT_KEYBOARD未启用；没有Input设备清单 | 当前缺按键驱动支持，不能仅归因于设备树遗漏 |
| PS SPI0/1 | 生效节点均disabled，SPI_SPIDEV未启用 | 当前没有该用户接口是配置结果 |
| PWM | CONFIG_PWM未启用 | 尚无标准PWM接口；专用PL驱动仍需另查 |
| I²C | i2c-0=AXI IIC、i2c-1=Cadence、i2c-2=DP AUX | 三条适配器已注册 |
| EEPROM | 0-0050存在，compatible=atmel,24c64；at24驱动目录存在；无driver链接、无eeprom文件 | 设备已描述和注册但未成功绑定；根因待查，未强制绑定／探测总线或写EEPROM |
| PL UART | ttyUL1；a00f0000.serial绑定uartlite | 驱动已绑定；本次未做外部双向收发 |
| Ethernet | eth0=NO-CARRIER、carrier=0；eth1 down，无IP | 没有已确认的外部网络通路，网络负载测试缺条件 |
| USB | 识别USB2／USB3 Hub，未见测试U盘块设备 | Hub存在；不代表外接存储读写通过 |
| eMMC／SD | mmcblk0、mmcblk1及挂载分区可见 | 未做写入测试；eMMC FAT仍有未正常卸载警告 |
| 温度 | AMS IIO的PS raw=43722，offset=-36058，scale=7.771514892 | 按(raw+offset)*scale/1000换算约59.56℃，仅一次采样 |
| PL温度 | raw=0 | 不作为有效温度用于长测判定 |
| VCU | devices_deferred包含a0240000.vcu | 依赖尚未就绪；模块加载不等于功能通过 |
| 测量工具 | cyclictest/stress-ng/stress/taskset/chrt/timeout均缺失 | 未进入实时延迟测量或压力测试 |

日志：01-identity.txt、02-baseline-hashes.txt、03-inventory.txt、04-dmesg.txt、05-resources.txt、06-hardware-detail.txt、07-deferred.txt。命令原文保存在同编号.sh；串口文本保留终端回显和回车控制字符。
