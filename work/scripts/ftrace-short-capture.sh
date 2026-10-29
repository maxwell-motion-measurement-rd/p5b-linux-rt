#!/bin/sh
# Run only after booting and verifying the separate diagnostic image.
set -eu
case "$(uname -r)" in *-diag-ftrace) ;; *) echo 'Diagnostic kernel required'; exit 2;; esac
test "$(cat /sys/kernel/realtime)" = 1
test "$(cat /sys/devices/system/cpu/online)" = 0-2
mkdir -p /tmp/rt-audit-tools
for tool in cyclictest rtload perf; do
    test -x "/tmp/rt-audit-tools/$tool" || cp "/opt/rt-diagnostics/$tool" "/tmp/rt-audit-tools/$tool"
done
trace=/sys/kernel/tracing
grep -q " $trace tracefs " /proc/mounts || mount -t tracefs nodev "$trace"
instance="$trace/instances/rt-audit"
test ! -e "$instance" || { echo 'Existing instance: export it before retry'; exit 2; }
mkdir "$instance"
out=/tmp/rt-ftrace-short
mkdir "$out"
cleanup() {
    echo 0 > "$instance/tracing_on"
    echo 0 > "$instance/events/enable"
}
trap cleanup EXIT INT TERM
echo 0 > "$instance/tracing_on"
echo nop > "$instance/current_tracer"
echo 7 > "$instance/tracing_cpumask"
echo 16384 > "$instance/buffer_size_kb"
echo mono > "$instance/trace_clock"
for event in sched/sched_waking sched/sched_wakeup sched/sched_switch irq/irq_handler_entry irq/irq_handler_exit irq/softirq_entry irq/softirq_exit; do
    test -f "$instance/events/$event/enable"
    echo 1 > "$instance/events/$event/enable"
done
cat "$instance/trace_clock" > "$out/trace_clock.txt"
echo > "$instance/trace"
echo 1 > "$instance/tracing_on"
/tmp/rt-audit-tools/cyclictest --laptop -a1 -t1 -p80 --policy=fifo -m -i1000 -D10 -q -h2000 > "$out/cyclictest.txt" 2>&1
echo 0 > "$instance/tracing_on"
cat "$instance/trace" > "$out/trace.txt"
for cpu in 0 1 2; do
    echo "CPU$cpu" >> "$out/buffer-stats.txt"
    cat "$instance/per_cpu/cpu$cpu/stats" >> "$out/buffer-stats.txt"
done
cleanup
gzip -c "$out/trace.txt" > "$out/trace.txt.gz"
sha256sum "$out"/*
echo 'Initial 10s idle capture only; inspect overrun and dropped events before interpretation.'
