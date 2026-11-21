#!/bin/sh
# Copy and install from macOS or Linux; keep existing captures on the board.
set -eu
host=${1:-${Q6A:-radxa@radxa-dragon-q6a.local}}
port=${2:-cam1}
case "$port" in cam1|cam2|cam3) ;; *) echo "Ожидается cam1, cam2 или cam3" >&2; exit 2;; esac
if [ "$#" -gt 2 ]; then echo "deploy.sh [ssh-host] [cam1|cam2|cam3]" >&2; exit 2; fi
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
stage=$(ssh -- "$host" 'mkdir -p ~/q6a-imx296 && cd ~/q6a-imx296 && mktemp -d .incoming.XXXXXXXX')
case "$stage" in .incoming.????????) ;; *) echo "Некорректное имя временного каталога" >&2; exit 1;; esac
case "$stage" in *[!a-zA-Z0-9.]* ) exit 1;; esac
trap 'ssh -- "$host" "rm -rf -- ~/q6a-imx296/$stage" </dev/null || :' EXIT
scp -- "$dir/install.py" "$dir/capture.py" "$dir/ports.py" "$dir/imx296-common.dtsi" \
    "$dir"/q6a-cam?-innomaker-imx296.dts "${host}:q6a-imx296/$stage/"
ssh -t -- "$host" "cd ~/q6a-imx296 && flock .deploy.lock sh -ec 'cd $stage && sudo python3 -B install.py --port $port && mv -f -- *.py *.dts *.dtsi ..'"
