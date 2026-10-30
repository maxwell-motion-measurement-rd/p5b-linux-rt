#!/bin/sh
set -eu
phase=${1:?idle cpu mem}
case "$phase" in idle|cpu|mem) ;; *) exit 2;; esac
base=/tmp/amp-g5
tools=/tmp/amp-r004
dir=$base/$phase
mkdir -p "$dir"
if test -f "$dir/started"; then echo PHASE_ALREADY_STARTED; exit 2; fi
cat /proc/uptime > "$dir/started"
loads=''
monitor=''
cleanup() {
    rc=$?
    trap - EXIT INT TERM
    if test -n "$monitor"; then kill "$monitor" 2>/dev/null || true; wait "$monitor" 2>/dev/null || true; fi
    for pid in $loads; do kill -TERM "$pid" 2>/dev/null || true; done
    for pid in $loads; do if wait "$pid"; then :; else rc=1; fi; done
    cat /proc/uptime > "$dir/finished"
    printf '%s\n' "$rc" > "$dir/exit-code"
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT TERM
dmesg > "$dir/dmesg-before.txt"
"$tools/g5_snapshot" > "$dir/snapshot-before.json"
cat /proc/stat > "$dir/stat-before.txt"
cat /proc/meminfo > "$dir/mem-before.txt"
if test "$phase" != idle; then
    for cpu in 0 1 2; do
        "$tools/g5_load" "$phase" "$cpu" 3600 > "$dir/load-$cpu.txt" 2>&1 &
        loads="$loads $!"
    done
    sleep 5
    for pid in $loads; do kill -0 "$pid"; done
fi
(
    while :; do
        printf 'SAMPLE '; cat /proc/uptime
        grep '^cpu' /proc/stat
        grep -E 'MemAvailable|MemFree|SwapFree' /proc/meminfo
        cat /sys/bus/platform/devices/core3-heartbeat/status
        cat /sys/bus/platform/devices/core3-heartbeat/stats
        sleep 10
    done
) > "$dir/telemetry.txt" 2>&1 &
monitor=$!
for mode in forward reverse cross; do
    printf 'MODE_BEGIN %s %s ' "$phase" "$mode"; cat /proc/uptime
    "$tools/g5_test" "$mode" 60000 > "$dir/$mode.json" 2> "$dir/$mode-progress.txt"
    mv "/tmp/amp-g5-$mode.latency-ns" "$dir/$mode.latency-ns"
    cat "$dir/$mode.json"
    "$tools/g5_snapshot" > "$dir/snapshot-after-$mode.json"
    if test "$phase" != idle; then for pid in $loads; do kill -0 "$pid"; done; fi
done
cat /proc/stat > "$dir/stat-after.txt"
cat /proc/meminfo > "$dir/mem-after.txt"
dmesg > "$dir/dmesg-after.txt"
cmp "$dir/dmesg-before.txt" "$dir/dmesg-after.txt"
printf 'PHASE_PASSED %s\n' "$phase"
