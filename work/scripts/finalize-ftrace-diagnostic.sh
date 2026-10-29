set -eu
root=/home/wang/p5-rt-diagnostics-20261029/kernel-image
test -f "$root/logs/BUILD_COMPLETE"
if test ! -f "$root/logs/diagnostic-tools-validation.json"; then
  python3 /home/wang/p5-rt-diagnostics-20261029/add-diagnostic-tools.py
fi
SOURCE_DATE_EPOCH=$(cat "$root/logs/source-date-epoch.txt") mkimage -f "$root/build/fit/p5b-rt.its" "$root/deploy/rt/image.ub" > "$root/logs/fit-build.log" 2>&1
python3 "$root/scripts/validate-fit.py"
dumpimage -l "$root/deploy/rt/image.ub" > "$root/logs/fit-listing.txt"
sha256sum "$root/deploy/rt/image.ub" > "$root/logs/image.sha256"
cmp "$root/build/dtb/system.dtb" /home/wang/p5b-rt-5.4.0/build/dtb/system.dtb
cmp "$root/deploy/rt/BOOT.BIN" /home/wang/p5b-rt-5.4.0/deploy/rt/BOOT.BIN
cmp "$root/deploy/rt/boot.scr" /home/wang/p5b-rt-5.4.0/deploy/rt/boot.scr
git -C /home/wang/p5b-rt-5.4.0/src diff --quiet
cat "$root/logs/kernelrelease.txt" "$root/logs/image.sha256"
