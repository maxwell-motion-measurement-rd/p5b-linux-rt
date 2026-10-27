# P5 实板与 P5B 工程名称说明

## 本次实际使用的板卡

2026-10-27 的 baseline 和 PREEMPT_RT 部署、串口检查均在正点原子 P5（XCZU4EV）板上完成。baseline 四核在线，RT 内核使用 A53 Core0／1／2。没有使用另一块 P5B 实板做并行对照。

现有工程、XSA 配套资料、设备树、启动镜像和日志沿用 P5B 命名。U-Boot／Linux 中的 `Alientek MpSoc-P5B Development Board` 是软件配置中的模型字符串，不能据此将本次实板写成 P5B。仓库名 p5b-linux-rt、构建路径、补丁路径和内核版本中的 p5b 保留，以维持日志、配置与交付包的对应关系。

## 资料检索结果

截至本次检索，在已查阅资料范围内，未发现 P5 与 P5B 在本次 Linux 部署所涉及配置上的明显差异。依据包括：

| 官方资料 | 可以确认的内容 |
| --- | --- |
| [正点原子资料下载中心](https://www.openedv.com/docs/build/html/index.html) | FPGA 开发板目录将两者合并列为“MPSoC - P5 / P5B开发板”，对应同一个资料入口 |
| [MPSoC-P5 / P5B 资料入口](https://www.openedv.com/docs/build/html/boards/fpga/zdyz-MPSOC-P5.html) | 官方目录链接的目标地址；本次抓取正文超时，因此不据此补写页面中未读取到的参数 |
| [正点原子 MPSoC-P5B 核心板产品页](https://www.alientek.com/Product_Details/122.html) | 当前官方产品命名包含 MPSoC-P5B；未提供本次已读取的、逐项列出 P5／P5B 差异的文字对照表 |
| [正点原子官方 P5 发布视频页面](https://www.bilibili.com/video/BV11u4y1M7nM/) | 官方使用过 MPSoC-P5 开发板名称；名称变化本身不证明硬件完全相同 |

这些资料和本次 P5 启动结果支持继续使用已验证工程记录，但不构成两种板卡全部硬件相同的证明。未逐项比对两版原理图、BOM、PCB 修订及所有接口资源，也未把原有视频、时钟、VCU 或 SPI NOR 问题归因于板型差异。

## 复现与验收范围

本仓库的实测结论指本次 P5 实板上的基本启动和 RT 三核运行。复现到其他实板或硬件修订时，应核对实际器件、内存、引脚与启动配置。完整外设、实时延迟及 AMP 共存仍待验收，不能用“未发现明显差异”替代这些测试。

结果与原始日志见 [baseline 记录](baseline-first-boot-20261027.md)、[RT 记录](rt-first-boot-20261027.md)；部署与复现步骤见 [README](../../README.md)。
