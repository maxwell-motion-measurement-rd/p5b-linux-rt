set -euo pipefail
export LC_ALL=C
root=/home/wang/p5b-rt-5.4.0
original=/home/wang/petalinux/ALIENTEK-MP/components/yocto/workspace/sources/linux-xlnx
cd "$root/src"
if grep -Ei 'FAILED|fuzz|Reversed|previously applied|Skipping' "$root/logs/patch-apply.log"; then exit 1; fi
test -z "$(find . -name '*.rej' -print -quit)"
patch --dry-run --reverse --batch --fuzz=0 -p1 < "$root/inputs/patch-5.4.3-rt1.patch" > "$root/logs/patch-reverse-check.log" 2>&1
git diff --stat > "$root/logs/patch-diff-stat.txt"
git diff --binary > "$root/logs/rt-applied.diff"
git status --porcelain=v1 --untracked-files=all > "$root/logs/worktree-after-patch.txt"
git -C "$original" --no-optional-locks status --porcelain=v1 --untracked-files=all > "$root/logs/original-source-status.after-step2.txt"
cmp "$root/logs/original-source-status.txt" "$root/logs/original-source-status.after-step2.txt"
printf 'DRY_RUN_FILES='; grep -c '^checking file ' "$root/logs/patch-dry-run.log"
printf 'PATCHED_FILES='; grep -c '^patching file ' "$root/logs/patch-apply.log"
tail -n 2 "$root/logs/patch-diff-stat.txt"
grep -n -A35 -B8 'config PREEMPT_RT' kernel/Kconfig.preempt
head -n 8 Makefile
cat localversion-rt
printf '\nNEW_FILES_AND_BACKUPS\n'
git ls-files --others --exclude-standard
printf '\nOFFSET_HUNKS\n'
grep 'succeeded at.*offset' "$root/logs/patch-apply.log" || true
touch "$root/logs/step2.complete"
printf '%s\n' RT_PATCH_APPLIED_AND_REVERSE_CHECK_OK
