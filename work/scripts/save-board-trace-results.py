from pathlib import Path
import hashlib,json,re

root=Path(__file__).resolve().parents[2]
run=root/'logs/rt-diagnostics/2026-10-29'
board=run/'board-trace'
analysis=json.loads((board/'trace-analysis.json').read_text(encoding='utf-8'))
post=json.loads((board/'postcheck.json').read_text(encoding='utf-8'))
transfer=json.loads((board/'trace-evidence.tar.gz.json').read_text(encoding='utf-8-sig'))
assert analysis[1]['event_count']==220415 and analysis[1]['full_requested_window_available']
assert post['kernel_log_identical'] and transfer['verified']
assert sum(c['bytes'] for c in transfer['chunks'])==1056409
result={'diagnostic_kernel_boot_verified':True,
    'boot_verification_scope':'Live kernel version/config, CPU flags, two loaded modules, image SHA256 and dmesg; no fresh full FSBL/U-Boot capture',
    'image_sha256':'c81f2203d00dcc086fb0e42dc7e321b71f52be94bcf22f2254e37e474edbb943',
    'ftrace_event_tests':analysis,
    'pmu_stat':{'duration_s':10,'cpu':2,'policy':'SCHED_OTHER','task_clock_ms':9961.98,
        'cycles':11943565134,'instructions':7956337962,'cache_misses':144742,
        'branch_misses':376226,'reported_running_percentage':100,'exit_code':0},
    'postcheck':post,'trace_instances_removed':True,'global_tracer':'nop',
    'global_events_enabled':False,'tracefs_left_mounted':True,'serial_released':True,
    'board_left_running_diagnostic_kernel':True,'previous_original_rt_spike_cause':'unresolved',
    'transfer_chunks_retried':[c['chunk'] for c in transfer['chunks'] if c['attempt']>1]}
(board/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
p=board/'report.md';s=p.read_text(encoding='utf-8')
s=s.replace('工具摘要与交付包一致，匹配模块已加载','工具摘要与交付包一致，dmaproxy和xlnx_vcu_core已加载')
s=s.replace('随后改用16KiB分块、逐块长度／SHA-256校验，并核对整个文件摘要后接受数据。','随后改用16KiB分块、逐块长度／SHA-256校验，并核对整个文件摘要后接受数据。65块中第31块（从0编号）重试一次后通过，其余块首次通过。')
p.write_text(s,encoding='utf-8')
p=run/'state.json';s=json.loads(p.read_text(encoding='utf-8'))
s.update(diagnostic_kernel_boot_verified=True,ftrace_executed=True,
    ftrace_status='10s idle event capture completed; first buffer overrun retained, 16MiB-per-CPU repeat complete with no loss',
    perf_hardware_diagnostic='cycles/instructions/cache-misses/branch-misses counted successfully',
    board_test_processes=[],serial_released=True,
    latest_board_report='logs/rt-diagnostics/2026-10-29/board-trace/report.md',
    next_step='Reproduce CPU/memory load on diagnostic version and correlate spikes; previous original RT tail latency unresolved.')
p.write_text(json.dumps(s,indent=2)+'\n',encoding='utf-8')
p=run/'report.md';s=p.read_text(encoding='utf-8')
entry='当前续接结果：诊断内核已启动，已完成10秒无丢失ftrace事件复测和A53 PMU计数验证。首次缓冲区覆盖及导出重试均保留记录；原始RT负载尖峰仍未定位。见[板端诊断实测报告](board-trace/report.md)。下文保留工具准备与部署阶段的记录。'
if entry not in s:
    i=s.index('\n\n');s=s[:i]+'\n\n'+entry+s[i:]
p.write_text(s,encoding='utf-8')
p=root/'docs/plans/rt-risk-assessment-state.json';s=json.loads(p.read_text(encoding='utf-8'))
s['diagnostics'].update(ftrace='Diagnostic kernel boot verified; 10s idle repeat complete, no buffer loss; original load spike unresolved',
    pmu='Diagnostic A53 cycles/instructions/cache-misses/branch-misses counts verified',
    latest_board_report='logs/rt-diagnostics/2026-10-29/board-trace/report.md')
p.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=root/'docs/plans/rt-diagnostics-execution-plan.md';s=p.read_text(encoding='utf-8')
entry='当前结果：诊断版本已上板，10秒ftrace空载复测无缓冲区覆盖／丢事件，A53硬件计数已验证；首次采集覆盖、传输重试及范围限制详见[板端报告](../../logs/rt-diagnostics/2026-10-29/board-trace/report.md)。此前原始RT负载尖峰仍需复现定位。'
if entry not in s:s=s.replace('## 原始环境与限制',entry+'\n\n## 原始环境与限制',1)
p.write_text(s,encoding='utf-8')
p=root/'README.md';s=p.read_text(encoding='utf-8')
s=s.replace('独立ftrace／PMU诊断镜像已构建并通过主机校验，尚未上板，ftrace未执行。','独立ftrace／PMU诊断镜像已启动，10秒空载事件复测无覆盖／丢事件，A53硬件计数已验证，原负载尖峰仍待定位。详见[板端实测](logs/rt-diagnostics/2026-10-29/board-trace/report.md)。')
p.write_text(s,encoding='utf-8')
for directory in [board,run]:
    files=sorted(p for p in directory.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
    (directory/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(directory).as_posix()}\n' for p in files),encoding='utf-8')
for doc in [board/'report.md',root/'docs/plans/rt-diagnostics-execution-plan.md']:
    for target in re.findall(r'\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
        if '://' not in target:assert (doc.parent/target).exists(),target
print('Saved verified board results, reports, checksums and continuation state.')
