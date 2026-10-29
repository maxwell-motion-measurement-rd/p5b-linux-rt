---
status: accepted
---

# 以未加入 ble.sh 的原始 RT 镜像作为首轮测量基准

2026-10-29，用户明确要求测试以原始 RT Linux 为标准，不使用 ble.sh 或额外的交互增强环境。首轮固定使用已归档的原始 RT 启动包，以便后续结果可以追溯到同一环境；PREEMPT_RT 仍为项目必选条件，本期不做非 RT 对照。

原始镜像自带的 Bash 和原有登录 Shell 保留，不将排除 ble.sh 解释为卸载或替换 Bash。测量工具作为单独记录版本的临时载荷提供；需要改内核、设备树或诊断配置时另编号，不能将其结果混写为原始 RT 基准结果。此决定没有认定 ble.sh 已造成实时性能问题，其影响尚未测量。

基准身份、执行前核对和阶段状态见[执行计划](../plans/rt-risk-assessment-execution-plan.md)与[状态文件](../plans/rt-risk-assessment-state.json)。
