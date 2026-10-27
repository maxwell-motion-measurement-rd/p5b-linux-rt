set -euo pipefail
project=/home/wang/petalinux/ALIENTEK-MP
root=/home/wang/p5b-rt-5.4.0
printf 'BUILD_STATUS\n'
if test -f "$root/logs/step5.exitcode"; then cat "$root/logs/step5.exitcode"; fi
tail -n 12 "$root/logs/kernel-build.log"
printf '\nEXTERNAL_MODULE_SOURCE_DIRECTORIES\n'
find "$project/build/tmp/work" -mindepth 2 -maxdepth 4 -type d \( -iname '*allegro*' -o -iname '*dmaproxy*' -o -iname '*vcu*' \) -print
printf '\nWORKSPACE_SOURCE_DIRECTORIES\n'
find "$project/components/yocto/workspace/sources" -mindepth 1 -maxdepth 1 -type d -printf '%f\n'
printf '\nMODULE_RECIPES\n'
find "$project/project-spec" -type f \( -iname '*dmaproxy*' -o -iname '*allegro*' -o -name '*.bb' \) -print | head -n 65
