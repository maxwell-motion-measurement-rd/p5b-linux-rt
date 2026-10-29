printf "__PERF_HEX_BEGIN__\n"; od -An -v -tx1 /tmp/rt-perf-diag/perf.data; printf "__PERF_HEX_END__\n"; sha256sum /tmp/rt-perf-diag/perf.data
