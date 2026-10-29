"""Summarize exported event traces; keep wake-to-dispatch separate from cyclictest latency."""
from pathlib import Path
from collections import Counter
import gzip, json, math, re

root = Path(__file__).resolve().parents[2]
run = root / 'logs/rt-diagnostics/2026-10-29/board-trace'
data = run / 'exported'

def timestamp_ns(value):
    sec, fraction = value.split('.')
    return int(sec)*10**9 + int(fraction.ljust(9,'0'))

def percentile(values, quantile):
    return values[math.ceil(len(values)*quantile)-1] if values else None

def analyze(name, complete):
    directory = data / name
    text = gzip.decompress((directory/'trace.txt.gz').read_bytes()).decode()
    lines = text.splitlines()
    events, unmatched = [], []
    pattern = re.compile(r'\[(\d+)\]\s+\S+\s+(\d+\.\d+):\s+(\w+):\s+(.*)$')
    for line in lines:
        if not line.strip() or line.startswith('#'): continue
        match = pattern.search(line)
        if not match:
            unmatched.append(line)
            continue
        cpu, clock, event, fields = match.groups()
        events.append((timestamp_ns(clock), int(cpu), event, fields, line))
    stats_text = (directory/'buffer-stats.txt').read_text()
    stats = {}
    for cpu, section in re.findall(r'CPU(\d+)\n(.*?)(?=CPU\d+\n|\Z)', stats_text, re.S):
        stats[cpu] = {k:int(v) for k,v in re.findall(r'^(entries|overrun|commit overrun|dropped events): (\d+)$',section,re.M)}
    assert not unmatched, unmatched[:3]
    assert len(events) == sum(s['entries'] for s in stats.values())
    if complete:
        assert all(not s['overrun'] and not s['commit overrun'] and not s['dropped events'] for s in stats.values())
    counts = Counter(e[2] for e in events)
    wake_pids, irq_names, softirqs, next_tasks = Counter(), Counter(), Counter(), Counter()
    for ns,cpu,event,fields,line in events:
        if event == 'sched_wakeup':
            m=re.search(r'comm=cyclictest pid=(\d+) .*target_cpu=0*1\b',fields)
            if m: wake_pids[int(m[1])] += 1
        if event == 'irq_handler_entry':
            m=re.search(r'irq=(\d+) name=(.*)',fields)
            if m: irq_names[m[1]+':'+m[2]]+=1
        if event == 'softirq_entry':
            m=re.search(r'\[action=(.*?)\]',fields)
            if m: softirqs[m[1]]+=1
        if event == 'sched_switch':
            m=re.search(r'next_comm=(.*?) next_pid=',fields)
            if m: next_tasks[m[1]]+=1
    measurement_pid = wake_pids.most_common(1)[0][0] if wake_pids else None
    pending, waking, pairs, waking_pairs = {}, {}, [], []
    worst = None
    for ns,cpu,event,fields,line in events:
        if event in ('sched_wakeup','sched_waking'):
            m=re.search(r'comm=cyclictest pid=(\d+)\b',fields)
            if m and int(m[1])==measurement_pid:
                (pending if event=='sched_wakeup' else waking)[measurement_pid]=ns
        elif event=='sched_switch':
            m=re.search(r'next_pid=(\d+)\b',fields)
            if not m or int(m[1])!=measurement_pid: continue
            if measurement_pid in pending:
                release=pending.pop(measurement_pid)
                delta=(ns-release)/1000
                assert delta>=0
                pairs.append(delta)
                if worst is None or delta>worst['delay_us']:
                    worst={'delay_us':delta,'wakeup_ns':release,'switch_ns':ns,'cpu':cpu}
            if measurement_pid in waking:
                delta=(ns-waking.pop(measurement_pid))/1000
                assert delta>=0
                waking_pairs.append(delta)
    ordered=sorted(pairs)
    if worst:
        context=[e[4] for e in events if worst['wakeup_ns']-100000<=e[0]<=worst['switch_ns']+100000]
        (run/(name+'-worst-dispatch-context.txt')).write_text('\n'.join(context)+'\n',encoding='utf-8')
    cyc=(directory/'cyclictest.txt').read_text()
    def cyclic(label):return int(re.search(r'^# '+label+r':\s*(\d+)',cyc,re.M).group(1))
    report={'capture':name,'full_requested_window_available':complete,'event_count':len(events),
        'buffer_stats':stats,'event_counts':dict(counts),'top_irq_handlers':irq_names.most_common(12),
        'softirq_entries':dict(softirqs),'top_scheduled_tasks':next_tasks.most_common(12),
        'cyclictest':{'samples':cyclic('Total'),'min_us':cyclic('Min Latencies'),
            'reported_avg_us':cyclic('Avg Latencies'),'max_us':cyclic('Max Latencies'),
            'histogram_overflows':cyclic('Histogram Overflows')},
        'measurement_pid_selected_by_wakeup_frequency_on_cpu1':measurement_pid,
        'cyclictest_cpu1_wakeup_counts':dict(wake_pids),
        'sched_wakeup_to_switch':{'matched_pairs':len(pairs),'min_us':min(pairs) if pairs else None,
            'mean_us':sum(pairs)/len(pairs) if pairs else None,'p99_us':percentile(ordered,.99),
            'p999_us':percentile(ordered,.999),'max_us':max(pairs) if pairs else None,'worst':worst},
        'sched_waking_to_switch_max_us':max(waking_pairs) if waking_pairs else None,
        'interpretation_limit':'Event-pair delay is not full periodic wakeup latency, execution time, or a proven worst-case bound.'}
    return report

results=[analyze('rt-ftrace-short',False),analyze('rt-ftrace-idle2',True)]
(run/'trace-analysis.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
for r in results: print(json.dumps(r))
