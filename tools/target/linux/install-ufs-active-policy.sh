#!/bin/bash
set -euo pipefail
task_defer=false
case "${1:-}" in
    '') ;;
    --defer) task_defer=true ;;
    *) echo 'Usage: sudo bash install-ufs-active-policy.sh [--defer]' >&2; exit 2 ;;
esac
test "$#" -le 1
test "$(id -u)" = 0 || { echo 'Run with sudo on Q6A' >&2; exit 1; }
c=/sys/bus/platform/devices/1d84000.ufshc
task_root=$(readlink -f "$(findmnt -n -o SOURCE /)")
task_parent=$(lsblk -dn -o PKNAME "$task_root")
task_root_device=$(readlink -f "/sys/class/block/$task_parent/device")
case "$task_root_device" in
    */1d84000.ufshc/host*/target*/*:0) ;;
    *) echo 'Root filesystem must be on UFS LUN 0' >&2; exit 1 ;;
esac
task_model_ok=false
for task_device in "$c"/host*/target*/*:0; do
    if [ -f "$task_device/model" ] && [ -f "$task_device/vendor" ] &&
       [ "$(tr -d '[:space:]' < "$task_device/model")" = THGJFCT2T84BAKCB ] &&
       [ "$(tr -d '[:space:]' < "$task_device/vendor")" = TOSHIBA ]; then
        task_model_ok=true
    fi
done
$task_model_ok || { echo 'Expected Toshiba UFS LUN 0 was not found' >&2; exit 1; }
task_tmp=$(mktemp -d)
trap 'rm -rf -- "$task_tmp"' EXIT
task_rule=99-z-q6a-toshiba-ufs-active.rules
cat > "$task_tmp/$task_rule" <<'RULES'
# Match cached SCSI inquiry data after the logical unit has been discovered.
ACTION=="add|bind|change", SUBSYSTEM=="scsi", KERNELS=="1d84000.ufshc", ATTR{vendor}=="TOSHIBA", ATTR{model}=="THGJFCT2T84BAKCB", ATTR{power/control}="on"
ACTION=="add|change", SUBSYSTEM=="scsi", KERNEL=="*:*:*:0", KERNELS=="1d84000.ufshc", ATTR{vendor}=="TOSHIBA", ATTR{model}=="THGJFCT2T84BAKCB", RUN+="/usr/lib/q6a/ufs-active-policy"
RULES
cat > "$task_tmp/ufs-active-policy" <<'HELPER'
#!/bin/sh
set -eu
c=/sys/bus/platform/devices/1d84000.ufshc
found=false
for d in "$c"/host*/target*/*:0; do
    if [ -f "$d/model" ] && [ -f "$d/vendor" ] &&
       [ "$(tr -d '[:space:]' < "$d/model")" = THGJFCT2T84BAKCB ] &&
       [ "$(tr -d '[:space:]' < "$d/vendor")" = TOSHIBA ]; then
        found=true
    fi
done
$found || exit 0
echo on > "$c/power/control"
for a in rpm_lvl spm_lvl auto_hibern8 clkgate_enable; do echo 0 > "$c/$a"; done
for p in "$c"/host*/target*/*/power/control; do echo on > "$p"; done
HELPER
cat > "$task_tmp/q6a-ufs-active" <<'HOOK'
#!/bin/sh
set -e
case "$1" in prereqs) exit 0 ;; esac
. /usr/share/initramfs-tools/hook-functions
copy_file executable /usr/lib/q6a/ufs-active-policy
HOOK
udevadm verify "$task_tmp/$task_rule"
install -d /usr/lib/q6a
for task_pair in "$task_rule:/etc/udev/rules.d/$task_rule" \
                 'ufs-active-policy:/usr/lib/q6a/ufs-active-policy' \
                 'q6a-ufs-active:/etc/initramfs-tools/hooks/q6a-ufs-active'; do
    task_source="$task_tmp/${task_pair%%:*}"
    task_destination=${task_pair#*:}
    if [ -e "$task_destination" ]; then
        cmp -- "$task_source" "$task_destination"
    else
        task_mode=0755
        [ "${task_pair%%:*}" != "$task_rule" ] || task_mode=0644
        install -m "$task_mode" -- "$task_source" "$task_destination"
    fi
done
if ! $task_defer; then
    udevadm control --reload-rules
    for task_control in "$c"/host*/target*/*/power/control; do
        udevadm trigger --action=change "${task_control%/power/control}"
    done
    udevadm settle
    test "$(cat "$c/power/control")" = on
    for a in rpm_lvl spm_lvl auto_hibern8 clkgate_enable; do
        test "$(cat "$c/$a")" = 0
    done
    for task_control in "$c"/host*/target*/*/power/control; do
        test "$(cat "$task_control")" = on
    done
fi
update-initramfs -u -k "$(uname -r)"
task_initrd="/boot/initrd.img-$(uname -r)"
lsinitramfs "$task_initrd" | grep -Fx "usr/lib/udev/rules.d/$task_rule"
lsinitramfs "$task_initrd" | grep -Fx 'usr/lib/q6a/ufs-active-policy'
cmp "$task_initrd" "/boot/efi/RadxaOS/$(uname -r)/initrd.img-$(uname -r)"
sha256sum "/etc/udev/rules.d/$task_rule" /usr/lib/q6a/ufs-active-policy \
    /etc/initramfs-tools/hooks/q6a-ufs-active "$task_initrd"
if $task_defer; then
    echo 'UFS active policy installed for the next boot'
else
    echo 'UFS active policy installation verified'
fi
