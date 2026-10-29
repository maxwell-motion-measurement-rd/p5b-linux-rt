printf '\n__DATA_BEGIN__\n'; cat /tmp/rt-audit-run/MEM.txt; printf '__DATA_END__\n'; sha256sum /tmp/rt-audit-run/MEM.txt; cat /tmp/rt-audit-run/MEM-load.txt
