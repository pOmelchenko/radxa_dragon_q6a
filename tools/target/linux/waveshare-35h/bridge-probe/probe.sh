#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
set -eu

if [ "$(id -u)" != 0 ]; then
    echo "Run with sudo sh probe.sh" >&2
    exit 1
fi

if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != --wait-active ]; }; then
    echo "Usage: sudo sh probe.sh [--wait-active]" >&2
    exit 2
fi

src=$(dirname "$(realpath "$0")")
work=$(mktemp -d)
loaded=0
trace_dir=
cleanup() {
    if [ -n "$trace_dir" ]; then
        echo nop > "$trace_dir/current_tracer"
        rmdir "$trace_dir"
    fi
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
snapshot=/sys/module/ws35h_icn6211/parameters/snapshot
if [ "$#" -eq 0 ]; then
    cat "$snapshot"
    exit
fi

root=/sys/kernel/tracing
[ -d "$root/instances" ] || root=/sys/kernel/debug/tracing
trace_dir=$(mktemp -d "$root/instances/ws35h.XXXXXX")
printf '%s\n' dsi_host_transfer msm_dsi_manager_cmd_xfer msm_dsi_host_cmd_rx \
    msm_dsi_host_power_on msm_dsi_host_power_off > "$trace_dir/set_ftrace_filter"
echo function > "$trace_dir/current_tracer"
echo 1 > "$trace_dir/tracing_on"

echo "Ready: press Shift on the Q6A keyboard if the screen is blank."
rejected=0
while :; do
    cat "$snapshot" > "$work/result" &
    reader=$!
    wait "$reader"
    # Only repeat the early -EINVAL seen on this kernel. Once dispatch is
    # reached, retain the very first reply or error from the active link.
    if ! grep -Fxq 'DSI read 0x00 returned -22 (expected 1 byte)' "$work/result"; then
        break
    fi
    awk -v pid="$reader" '$1 == ("cat-" pid)' "$trace_dir/trace" > "$work/calls"
    if ! grep -qw dsi_host_transfer "$work/calls" ||
            grep -qw msm_dsi_manager_cmd_xfer "$work/calls"; then
        break
    fi
    rejected=$((rejected + 1))
    if [ "$rejected" -ge 30 ]; then
        echo "Timed out waiting for DSI command dispatch."
        break
    fi
    sleep 1
done
printf 'Early rejections: %s\n' "$rejected"
cat "$work/result"
echo "Watching DSI host power calls for 10 more seconds..."
echo WS35H_OBSERVE > "$trace_dir/trace_marker"
sleep 10
echo 0 > "$trace_dir/tracing_on"
echo "Last read (first three calls):"
awk -v pid="$reader" '$1 == ("cat-" pid) {print; if (++n == 3) exit}
    END {if (!n) print "(no trace for reader)"}' "$trace_dir/trace"
echo "Host power calls (WS35H_OBSERVE marks the final 10 seconds):"
awk '/: msm_dsi_host_power_(on|off)([[:space:]]|$)/ || /tracing_mark_write: WS35H_OBSERVE/' "$trace_dir/trace"
