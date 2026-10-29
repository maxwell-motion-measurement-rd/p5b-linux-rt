import hashlib,json,math,re
from pathlib import Path
root=Path(__file__).resolve().parents[2]
run=root/'logs/rt-risk/2026-10-29/103809-tools'
results=[]
for name,duration in [('T00',600),('CPU',60),('MEM',60),('CPU-repeat',60)]:
    p=run/(name+'-histogram.txt')
    if not p.exists(): continue
    t=p.read_text()
    bins=[(int(a),int(b)) for a,b in re.findall(r'^(\d+)\s+(\d+)\s*$',t,re.M)]
    def value(label):
        m=re.search(r'^# '+re.escape(label)+r':\s*(\d+)',t,re.M)
        if not m: raise ValueError(label)
        return int(m.group(1))
    count=value('Total'); over=value('Histogram Overflows')
    assert sum(n for _,n in bins)+over==count
    def quantile(q):
        target=math.ceil(count*q); n=0
        for us,freq in bins:
            n+=freq
            if n>=target: return us
        return None
    results.append({'case':name,'duration_s':duration,'samples':count,'min_us':value('Min Latencies'),
        'reported_avg_us':value('Avg Latencies'),'max_us':value('Max Latencies'),
        'p99_histogram_bin_us':quantile(.99),'p999_histogram_bin_us':quantile(.999),
        'observations_strictly_above_1000us':sum(n for us,n in bins if us>1000),
        'histogram_overflows':over,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(run/'measurements.json').write_text(json.dumps(results,indent=2)+'\n')
for r in results: print(json.dumps(r))
