printf '\n__DATA_BEGIN__\n'; cat /tmp/rt-audit-run/CPU.txt; printf '__DATA_END__\n'; sha256sum /tmp/rt-audit-run/CPU.txt; cat /tmp/rt-audit-run/CPU-load0.txt /tmp/rt-audit-run/CPU-load2.txt
