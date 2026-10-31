"""Draw measured P5 results only; verify plotted statistics against raw evidence."""
import sys,pathlib,json,hashlib,re,tarfile,csv,io,os
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'work/plot-deps'))
os.environ['MPLCONFIGDIR']=str(ROOT/'work/matplotlib-cache')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
OUT=ROOT/'docs/reports/figures/test-results-20261031'
OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,
 'font.size':11,'axes.titlesize':14,'figure.facecolor':'#f8fafc',
 'axes.facecolor':'white','axes.spines.top':False,'axes.spines.right':False,
 'axes.labelcolor':'#334155','text.color':'#17243b','xtick.color':'#475569','ytick.color':'#475569',
 'svg.fonttype':'none'})
COLORS=['#2563eb','#d97706','#0d9488','#a855f7']
sources={}
def source(name):
 p=ROOT/name;b=p.read_bytes();sources[name]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b
def obj(name):return json.loads(source(name))
def finish(fig,name,title,note,source_label):
 fig.suptitle(title,x=.055,y=.98,ha='left',fontsize=19,fontweight='bold')
 fig.text(.055,.045,note,fontsize=10,color='#475569',va='bottom')
 fig.text(.055,.014,'来源：'+source_label,fontsize=8,color='#64748b')
 fig.subplots_adjust(left=.08,right=.97,top=.80,bottom=.24,wspace=.28)
 for ext in ('png','svg'):fig.savefig(OUT/(name+'.'+ext),dpi=160)
 plt.close(fig)
def tidy(ax):ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)

rtbase='logs/rt-risk/2026-10-29/103809-tools/'
rt=obj(rtbase+'measurements.json');rt_samples={}
names={'T00':'空载冒烟','CPU':'CPU 负载','MEM':'内存负载','CPU-repeat':'CPU 复测'}
for row in rt:
 b=source(rtbase+row['case']+'-histogram.txt')
 assert hashlib.sha256(b).hexdigest()==row['sha256']
 hist=np.array([(int(a),int(b))for a,b in re.findall(rb'(?m)^(\d+)\s+(\d+)\s*$',b)],dtype=np.int64)
 assert len(hist)==2000 and hist[:,1].sum()==row['samples'] and row['histogram_overflows']==0
 a=np.repeat(hist[:,0],hist[:,1]);rt_samples[row['case']]=a
 assert a.min()==row['min_us'] and a.max()==row['max_us']
 for key,p in [('p99_histogram_bin_us',.99),('p999_histogram_bin_us',.999)]:
  assert a[int(np.ceil(len(a)*p))-1]==row[key]
 assert int((a>1000).sum())==row['observations_strictly_above_1000us']
labels=[names[r['case']]+f"\n{r['duration_s']}s · N={r['samples']:,}"for r in rt]
fig,axes=plt.subplots(1,2,figsize=(14,6.5));x=np.arange(4)
for i,(key,label)in enumerate([('reported_avg_us','平均'),('p99_histogram_bin_us','P99'),('p999_histogram_bin_us','P99.9')]):
 vals=[r[key]for r in rt];bars=axes[0].bar(x+(i-1)*.24,vals,.23,label=label,color=COLORS[i]);axes[0].bar_label(bars,padding=3,fontsize=9)
axes[0].set_ylim(0,88);axes[0].set_title('常态与分布尾部');axes[0].legend(ncol=3,frameon=False,loc='upper left');axes[0].set_ylabel('唤醒延迟 / µs')
bars=axes[1].bar(x,[r['max_us']for r in rt],color=COLORS[0],width=.55);axes[1].bar_label(bars,padding=5)
axes[1].axhline(1000,color='#be123c',ls='--',lw=1.2,label='1000µs 探针周期');axes[1].set_ylim(0,1530);axes[1].set_title('观测最大值');axes[1].set_ylabel('唤醒延迟 / µs');axes[1].legend(frameon=False,loc='upper left')
for ax in axes:ax.set_xticks(x,labels,fontsize=9);tidy(ax)
finish(fig,'01-kernel-latency','内核测试｜常态延迟较低，仍观测到超过 1ms 的尾部',
 '2026-10-29 · 原始 RT · cyclictest 绑定 CPU1，1ms 周期，FIFO 优先级80。\n空载600秒、其余各60秒；最大值受观测时长影响。1000µs 是探针周期，非产品验收线。',
 'measurements.json ＋ 四份原始直方图（均已核对摘要与样本数）')

fig,axes=plt.subplots(1,2,figsize=(14,6.5))
for i,row in enumerate(rt):
 a=rt_samples[row['case']];u,c=np.unique(a,return_counts=True)
 axes[0].step(u,np.cumsum(c)/len(a)*100,where='post',color=COLORS[i],label=names[row['case']],lw=2)
 tail=(len(a)-np.cumsum(c)+c)/len(a)*100
 axes[1].step(u,tail,where='pre',color=COLORS[i],label=names[row['case']],lw=1.7)
axes[0].set_xlim(35,90);axes[0].set_ylim(0,102);axes[0].set_title('主要分布：横轴放大至35—90µs');axes[0].set_ylabel('延迟 ≤ 横轴值的样本比例 / %')
axes[1].set_yscale('log');axes[1].set_xlim(35,1350);axes[1].set_ylim(1e-4,110);axes[1].set_title('尾部分布：纵轴为对数刻度');axes[1].set_ylabel('延迟 ≥ 横轴值的样本比例 / %');axes[1].axvline(1000,color='#be123c',ls='--',lw=1)
for ax in axes:ax.set_xlabel('唤醒延迟 / µs');ax.legend(frameon=False,fontsize=9);tidy(ax)
finish(fig,'02-kernel-distribution','内核测试｜真实直方图显示常态与稀有尖峰并存',
 '由1µs直方图直接累计，未拟合或补造样本。右图绘至各组最大值，超过最大值后的0比例不绘于对数轴。\n各组时长与样本数不同；CPU 首测／内存负载严格超过1000µs的样本分别为1／2个，空载与复测为0。',
 'T00／CPU／MEM／CPU-repeat-histogram.txt')

ampbase='logs/amp/2026-10-30/g5/'
pressure=obj(ampbase+'pressure-results.json');overall=obj(ampbase+'results.json')
archive=source(ampbase+'amp-g5-evidence.tar.gz')
assert hashlib.sha256(archive).hexdigest()==overall['evidence_archive_sha256']
samples={};rows=[]
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz')as tar:
 for phase in ('idle','cpu','mem'):
  for mode in ('forward','reverse','cross'):
   b=tar.extractfile(f'amp-g5/{phase}/{mode}.latency-ns').read()
   pairs=np.loadtxt(io.BytesIO(b),dtype=np.int64)
   assert np.array_equal(pairs[:,0],np.arange(60000))
   a=pairs[:,1];assert np.all(a>0);samples[phase,mode]=a
   s=np.sort(a);r=pressure['phases'][phase]['modes'][mode]
   assert r['passed']==len(a)==60000 and r['errors']==0 and r['missed_release']==0
   metrics={'min_us':int(s[0]//1000),'max_us':int(s[-1]//1000),'mean_us':int(s.sum()//len(a)//1000)}
   for key,p in [('p50_us',500),('p95_us',950),('p99_us',990),('p999_us',999)]:metrics[key]=int(s[(len(a)*p+999)//1000-1]//1000)
   assert all(r[k]==v for k,v in metrics.items()),(phase,mode,metrics)
   rows.append({'condition':phase,'mode':mode,'N':len(a),**metrics,'errors':r['errors']})
assert sum(r['N']for r in rows)==overall['pressure_transactions']==540000
assert max(r['max_us']for r in rows)==overall['max_observed_transaction_latency_us']==4024
phases={'idle':'空载','cpu':'CPU 负载','mem':'内存负载'}
modes={'forward':'正向','reverse':'反向完整事务','cross':'交叉完整事务'}
fig,axes=plt.subplots(1,3,figsize=(15,6.7));x=np.arange(3)
for ax,(mode,label)in zip(axes,modes.items()):
 for i,(key,name)in enumerate([('mean_us','平均'),('p99_us','P99'),('max_us','最大')]):
  vals=[pressure['phases'][p]['modes'][mode][key]for p in phases]
  bars=ax.bar(x+(i-1)*.25,vals,.24,color=COLORS[i],label=name);ax.bar_label(bars,padding=3,fontsize=8)
 ax.set_title(label);ax.set_xticks(x,list(phases.values()));ax.set_ylim(0,4700);ax.set_ylabel('事务耗时 / µs');tidy(ax)
axes[0].legend(frameon=False,ncol=3,loc='upper left')
finish(fig,'03-communication-latency','Linux 与 Core3｜通信长测的平均、P99 与最大耗时',
 '2026-10-30 · 每种条件30分钟，每模式10分钟／60000笔；目标100Hz，9组共540000笔。\n反向与交叉事务包含两步交互。最大观测值4024µs；这是事务耗时，不能与cyclictest唤醒延迟直接排名。',
 'G5 pressure-results.json ＋ 已校验的证据包内9份逐笔延迟')

fig,axes=plt.subplots(1,3,figsize=(15,6.7))
for ax,(mode,label)in zip(axes,modes.items()):
 for i,phase in enumerate(phases):
  a=np.sort(samples[phase,mode])/1000
  # Use all distinct observations, keeping the exact empirical distribution.
  u,c=np.unique(a,return_counts=True)
  ax.step(u,np.cumsum(c)/len(a)*100,where='post',color=COLORS[i],lw=1.6,label=phases[phase])
 ax.set_title(label);ax.set_xlim(0,4200);ax.set_ylim(0,102);ax.set_xlabel('事务耗时 / µs');ax.set_ylabel('耗时 ≤ 横轴值的事务比例 / %');tidy(ax)
axes[0].legend(frameon=False,loc='lower right')
finish(fig,'04-communication-distribution','Linux 与 Core3｜54万笔实测事务的累计分布',
 '每条曲线60000笔，逐笔纳秒数据转换为微秒；未抽样、插值或拟合。\nCPU条件：三核普通整数负载；内存条件：三个256MiB进程。正常长测新增通信错误与missed_release均为0。',
 'amp-g5-evidence.tar.gz 内 idle／cpu／mem 的 forward／reverse／cross.latency-ns')

tr=obj('logs/rt-diagnostics/2026-10-29/board-trace/trace-analysis.json')
valid=[r for r in tr if r['full_requested_window_available']];assert len(valid)==1
tr=valid[0];events=tr['event_counts'];assert sum(events.values())==tr['event_count']==220415
assert all(v[k]==0 for v in tr['buffer_stats'].values()for k in ('overrun','commit overrun','dropped events'))
fig,axes=plt.subplots(1,2,figsize=(14,6.5));ax=axes[0]
display={'sched_switch':'任务切换','sched_waking':'开始唤醒','sched_wakeup':'唤醒事件','irq_handler_entry':'IRQ进入','irq_handler_exit':'IRQ退出','softirq_entry':'softirq进入','softirq_exit':'softirq退出'}
keys=list(display);bars=ax.barh(np.arange(7),[events[k]for k in keys],color=COLORS[0]);ax.bar_label(bars,padding=4,fmt='{:,.0f}',fontsize=9);ax.set_yticks(np.arange(7),[display[k]for k in keys]);ax.invert_yaxis();ax.set_xlim(0,105000);ax.set_xlabel('记录事件数');ax.set_title('完整复测：共220415条事件')
d=tr['sched_wakeup_to_switch'];ax=axes[1];ks=['min_us','mean_us','p99_us','p999_us','max_us'];vals=[d[k]for k in ks]
bars=ax.bar(np.arange(5),vals,color=COLORS[2],width=.55);ax.bar_label(bars,labels=[f'{v:.2f}'if k=='mean_us'else f'{v:g}'for k,v in zip(ks,vals)],padding=5);ax.set_xticks(np.arange(5),['最小','平均','P99','P99.9','最大']);ax.set_ylim(0,6.4);ax.set_ylabel('间隔 / µs');ax.set_title(f"唤醒事件 → 调入：{d['matched_pairs']:,}对");tidy(ax)
finish(fig,'05-diagnostic-trace','诊断内核｜完整跟踪复测与局部调度间隔',
 '2026-10-29 · 诊断版10秒空载，16MiB／核；各核覆盖／丢弃计数为0。首次4MiB覆盖记录未混入本图。\n事件对间隔只覆盖局部路径；同期cyclictest最大唤醒延迟86µs。不能据此认定负载尖峰已修复。',
 'board-trace/trace-analysis.json（rt-ftrace-idle2）')

with (OUT/'communication-metrics.csv').open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(OUT/'provenance.json').write_text(json.dumps({'sources':sources,'validation':{'rt_histograms':4,'amp_raw_samples':540000,'amp_statistic_groups':9,'trace_events':220415,'all_assertions_passed':True},'metric_rules':{'rt_percentiles':'nearest rank on 1us histogram','amp_percentiles':'nearest rank on raw ns, integer division to us, matching board summary','rt_mean':'tool-reported integer mean','amp_mean':'integer mean, truncated to us'},'no_simulated_data':True},ensure_ascii=False,indent=2),encoding='utf-8')
print('OK: 5 figures, PNG + SVG; 4 RT histograms and 540000 AMP samples verified.')
