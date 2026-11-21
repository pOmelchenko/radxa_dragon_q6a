#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
set -eu

if [ "$(id -u)" != 0 ]; then
    echo "Run with sudo sh probe.sh" >&2
    exit 1
fi

src=$(dirname "$(realpath "$0")")
work=$(mktemp -d)
loaded=0
cleanup() {
    if [ "$loaded" = 1 ]; then
        rmmod ws35h_icn6211
    fi
    rm -rf "$work"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

cp "$src/ws35h_icn6211.c" "$work/"
echo 'obj-m := ws35h_icn6211.o' > "$work/Kbuild"
make -s -C "/lib/modules/$(uname -r)/build" M="$work" modules
insmod "$work/ws35h_icn6211.ko"
loaded=1
cat /sys/module/ws35h_icn6211/parameters/snapshot
