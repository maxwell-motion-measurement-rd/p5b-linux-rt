set -euo pipefail
root=/home/wang/p5b-rt-5.4.0
dtb=$root/inputs/system.dtb
mkdir -p "$root/build/dtb"
dtc -I dtb -O dts -o "$root/build/dtb/original.dts" "$dtb" 2> "$root/logs/dtb-original-warnings.txt"
sed -n '1,210p' "$root/build/dtb/original.dts"
printf '\nCPU3_REFERENCES\n'
for i in 0 1 2 3; do
  printf 'cpu@%s reg=' "$i"; fdtget -t x "$dtb" /cpus/cpu@$i reg
  printf 'cpu@%s phandle=' "$i"; fdtget -t x "$dtb" /cpus/cpu@$i phandle || true
done
grep -n -A20 -B6 -E 'cpu-map|cooling-maps|__symbols__|cpu3 =|chosen \{' "$root/build/dtb/original.dts" || true
printf '\nDEVICE_TREE_INPUTS\n'
find "$root/inputs/device-tree" -maxdepth 1 -printf '%f %l\n' | head -n 50
printf '\nKERNEL_CPU_ITERATION\n'
grep -n -A10 -B8 -E 'for_each_of_cpu_node|of_get_next_cpu_node' "$root/src/include/linux/of.h" "$root/src/drivers/of/base.c"
