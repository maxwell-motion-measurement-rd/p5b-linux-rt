#!/bin/sh
set -eu
trial_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -t 0 ] || [ ! -t 1 ]; then
    echo 'Run this launcher in an interactive serial or SSH terminal.' >&2
    exit 1
fi
bash_bin=/bin/bash.bash
if [ ! -x "$bash_bin" ]; then
    bash_bin=$(command -v bash) || { echo 'Bash is required.' >&2; exit 1; }
fi
for tool in awk sed grep stty tty date mkdir mktemp rm cat sort head tail wc readlink sleep od chmod; do
    command -v "$tool" >/dev/null 2>&1 || { echo "Missing required command: $tool" >&2; exit 1; }
done
P5_BLESH_DIR=$trial_dir
export P5_BLESH_DIR
"$bash_bin" --noprofile --rcfile "$trial_dir/bashrc" -i
