set -euo pipefail
project=/home/wang/petalinux/ALIENTEK-MP
root=/home/wang/p5b-rt-5.4.0
strings "$project/images/linux/boot.scr" > "$root/logs/boot-script.txt"
strings "$project/images/linux/u-boot.bin" | grep -E '^(bootargs=|bootcmd=|boot_targets=|boot_scripts=|fdt_high=|initrd_high=|bootm_size=|kernel_addr_r=|fdt_addr_r=|ramdisk_addr_r=)' > "$root/logs/u-boot-default-environment.txt"
cat "$root/logs/u-boot-default-environment.txt"
printf '\nBOOT_SCRIPT\n'
cat "$root/logs/boot-script.txt"
printf '\nUBOOT_CONFIGS\n'
find "$project/build/tmp/work" -maxdepth 5 -path '*u-boot*' -name '.config' -type f -print | while read -r file; do
  printf '%s\n' "$file"
  grep -E 'CONFIG_(USE_BOOTARGS|BOOTARGS|SYS_BOOTM_LEN|ENV_IS_NOWHERE|BOOTCOMMAND)' "$file" || true
done
