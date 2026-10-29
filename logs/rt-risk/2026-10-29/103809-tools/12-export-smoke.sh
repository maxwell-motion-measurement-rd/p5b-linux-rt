printf '\n__DATA_BEGIN__\n'; cat /tmp/rt-audit-run/T00.txt; printf '__DATA_END__\n'; sha256sum /tmp/rt-audit-run/T00.txt
