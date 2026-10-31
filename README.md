# P5 Linux实时部署与Linux／Core3通信

本仓库面向首次接触项目的组内成员，保存P5（XCZU4EV）学习板上的实时内核移植、启动部署、内核测量和最小核间通信成果，以及复现方法和问题处理证据。软件目录沿用P5B名称，实测板为P5；其他硬件修订须重新核对。

**截至2026-10-31：** RT三核启动、内核短测与诊断链路、Linux CPU0—2与Core3双向最小通信均已完成相应验证。通信正常长测540000笔、故障恢复与5次冷启动通过；原始RT的1255／1293µs唤醒尖峰仍未定位。真实控制环、电机、产品核心板与硬实时指标未验收。r004断电后仍需手动重载，自动启动暂缓。

## 按你的目的阅读

| 你想了解什么 | 从这里开始 | 阅读后能得到什么 |
| --- | --- | --- |
| 只看项目目前最终做到了什么 | **[完整成果报告](docs/reports/PROJECT-REPORT.md)** | 目标、实现、完整实测结果与图表、交付物、问题和未完成范围；无需先阅读过程日志 |
| 从零理解项目并动手复现 | **[项目理解与复现指南](docs/GETTING-STARTED.md)** | 架构与版本区别、所需材料、已验证包重放／源码重建／离线核验三种路径，以及预期结果与停止条件 |
| 查遇到过什么问题、为什么、怎么处理 | **[问题与处理记录](docs/TROUBLESHOOTING.md)** | 症状、已确认原因、处理、验证证据与仍未解决的问题，区分推测和确认结论 |

不熟悉项目时，先读复现指南的运行结构与前置条件，再选择路线；只需要组内汇报结论，直接读完整成果报告。

## 操作与证据索引

| 具体任务 | 文档／产物 |
| --- | --- |
| 下载启动包、部署SD、核对版本及回退 | [部署指南](docs/DEPLOY.md) · [baseline／原始RT Release](https://github.com/maxwell-motion-measurement-rd/p5b-linux-rt/releases/tag/board-boot-20261027) |
| 从固定厂商源码重建RT | [源码重建](docs/build/REPRODUCE.md) · [内核提交备份](docs/build/kernel-git-backup.md) |
| 重放通信实验或构建r004 | [通信构建与手动加载](docs/build/AMP-REPRODUCE.md) · [通信手动快照Release](https://github.com/maxwell-motion-measurement-rd/p5b-linux-rt/releases/tag/amp-comm-validation-20261030) |
| 了解内核工具、参数和结果口径 | [内核测试方法与结果](docs/reports/rt-assessment-summary-20261029.md) |
| 查看通信实现、消息／故障／长测细节 | [通信阶段总览](docs/reports/amp-stage-summary-20261030.md) · [G3消息](docs/reports/amp-g3-validation-20261030.md) · [G4故障](docs/reports/amp-g4-validation-20261030.md) · [G5长测](docs/reports/amp-g5-validation-20261030.md) |
| 查看全部图表与制图来源 | [测试结果图集](docs/reports/test-results-visualization-20261031.md) |

## 复现前必须知道

原始RT包与通信基础包不能混用：原始RT的FIT（Flattened Image Tree，多载荷启动镜像）不含通信所需内存预留。仅让Linux运行三核不等于通信已实现。

已验证的通信环境由两部分配合运行，r001和r004是本实验的修订编号：

- **r001基础启动包放在SD卡上。** 上电后由它启动Linux，并通过设备树为Core3程序和双方通信预留内存空间。
- **r004通信载荷在Linux启动后手动加载到RAM。** 它包括Linux通信模块和Core3裸机程序。核对载荷与Core3关断状态后，手动请求单次启动Core3，再运行通信测试。

完整顺序是：**SD卡启动r001 → 手动加载r004 → 核对状态并启动Core3 → 运行双向通信测试**。r004没有写进SD启动包；断电后SD卡上的r001仍在，RAM中的r004会丢失，下次上电需要重新加载。当前尚未配置开机自动恢复通信。具体操作见[通信构建与手动加载指南](docs/build/AMP-REPRODUCE.md)。

Release提供已验证的手动部署文件，访问需要仓库权限；GitHub的“Download ZIP”是源码与资料，不是启动包。从源码重建另需匹配的原厂商工程、工具链、硬件输入与rootfs，仓库未包含全部依赖。

内核唤醒延迟、通信完整事务耗时和局部调度间隔是三种不同测量；由于测量对象、计时起止点和测试条件不同，不能仅按数值大小判断哪种方案的实时性更好；测试中记录到的最大耗时，也只是在该次测试条件和样本范围内观察到的最大值，不能保证产品在所有运行条件下都不会超过这一数值。

## 仓库布局与文档约定

- `docs/GETTING-STARTED.md`、`docs/TROUBLESHOOTING.md`、`docs/reports/PROJECT-REPORT.md`是三条主要阅读入口。
- `configs/`、`patches/`保存固定配置、启动镜像模板和源码变更；`amp/`保存各阶段程序、协议与测试工具，最终源码位置以通信指南为准。
- `work/scripts/`保存构建和分析方法；历史脚本含原环境路径，使用前按指南替换，不能直接当作通用安装器。
- `logs/board/`、`logs/rt-risk/`、`logs/rt-diagnostics/`、`logs/amp/`保存原始证据、结构化结果与摘要。
- `docs/adr/`、`docs/board/`和日期报告保留当期决策、状态与失败记录。当前总体完成范围以完整成果报告为准，历史“尚未完成”不自动成为当前待办。

后续维护时，新的实验先保存独立证据和条件，再更新对应复现／问题文档，最后更新完整成果报告与本页日期。原因未确认就标为未定位；图表必须能追溯到原始记录。保留失败与采集缺口，不以新结果覆盖旧数据。
