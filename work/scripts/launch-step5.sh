set -euo pipefail
root=/home/wang/p5b-rt-5.4.0
test -f "$root/scripts/step5-build.sh"
test ! -e "$root/logs/step5.pid"
nohup bash "$root/scripts/step5-build.sh" </dev/null > "$root/logs/step5-driver.log" 2>&1 &
pid=$!
printf '%s\n' "$pid" > "$root/logs/step5.pid"
printf 'BUILD_STARTED pid=%s\n' "$pid"
