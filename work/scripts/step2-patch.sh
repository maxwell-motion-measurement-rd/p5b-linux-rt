set -euo pipefail
export LC_ALL=C
root=/home/wang/p5b-rt-5.4.0
original=/home/wang/petalinux/ALIENTEK-MP/components/yocto/workspace/sources/linux-xlnx
test -f "$root/logs/step1.complete"
test ! -e "$root/src"
exec > >(tee "$root/logs/step2-patch.log") 2>&1
git -C "$original" worktree add --detach "$root/src" 62ea514294a0c9a80455e51f1f4de36e66e8c546
cd "$root/src"
git status --porcelain=v1 --untracked-files=all > "$root/logs/worktree-before-patch.txt"
test ! -s "$root/logs/worktree-before-patch.txt"
patch --dry-run --batch --fuzz=0 -p1 < "$root/inputs/patch-5.4.3-rt1.patch" > "$root/logs/patch-dry-run.log" 2>&1
patch --batch --fuzz=0 -p1 < "$root/inputs/patch-5.4.3-rt1.patch" > "$root/logs/patch-apply.log" 2>&1
if grep -Ei 'FAILED|fuzz|Reversed|previously applied|Skipping' "$root/logs/patch-apply.log"; then exit 1; fi
test -z "$(find . -name '*.rej' -print -quit)"
git diff --stat > "$root/logs/patch-diff-stat.txt"
git diff --binary > "$root/logs/rt-applied.diff"
git status --porcelain=v1 --untracked-files=all > "$root/logs/worktree-after-patch.txt"
git -C "$original" --no-optional-locks status --porcelain=v1 --untracked-files=all > "$root/logs/original-source-status.after-step2.txt"
cmp "$root/logs/original-source-status.txt" "$root/logs/original-source-status.after-step2.txt"
printf 'DRY_RUN_FILES='; grep -c '^checking file ' "$root/logs/patch-dry-run.log"
printf 'PATCHED_FILES='; grep -c '^patching file ' "$root/logs/patch-apply.log"
tail -n 2 "$root/logs/patch-diff-stat.txt"
grep -n -A65 -B12 'config PREEMPT_RT' kernel/Kconfig.preempt
head -n 8 Makefile
git ls-files --others --exclude-standard
touch "$root/logs/step2.complete"
printf '%s\n' RT_PATCH_APPLIED_OK
