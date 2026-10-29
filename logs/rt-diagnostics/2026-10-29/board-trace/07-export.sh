printf "__TRACE_HEX_BEGIN__\n"; od -An -v -tx1 /tmp/rt-trace-evidence.tar.gz | tr -d " \n"; printf "\n__TRACE_HEX_END__\n"; sha256sum /tmp/rt-trace-evidence.tar.gz
