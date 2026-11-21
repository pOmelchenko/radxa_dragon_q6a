#!/usr/bin/env python3
"""Установить IMX296 в существующую конфигурацию Radxa Dragon Q6A."""
import argparse
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

from ports import PORTS

HERE = Path(__file__).resolve().parent
ESP = Path("/boot/efi")
MODULES = ("i2c-qcom-cci", "imx296", "qcom_camss")


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def efi_file(esp, name):
    path = PurePosixPath(name)
    if path.root != "/" or ".." in path.parts or "\\" in name:
        raise ValueError(f"Недопустимый путь EFI: {name}")
    target = esp.joinpath(*path.parts[1:])
    if not target.resolve().is_relative_to(esp.resolve()):
        raise ValueError(f"Путь вне EFI: {name}")
    return target


def dependencies():
    packages = {"device-tree-compiler": ("dtc", "fdtoverlay", "fdtget"),
                "v4l-utils": ("media-ctl", "v4l2-ctl"), "kmod": ("modinfo", "modprobe"),
                "cpp": ("cpp",)}
    missing = [pkg for pkg, cmds in packages.items() if not all(shutil.which(c) for c in cmds)]
    if missing:
        subprocess.run(["apt-get", "install", "-y", "--no-remove", "--no-install-recommends",
                        *missing], check=True)


def fields(lines, key):
    return [line.split()[1:] for line in lines if line.split()[:1] == [key]]


def single_path(lines, key):
    rows = fields(lines, key)
    if len(rows) != 1 or len(rows[0]) != 1:
        raise ValueError(f"В записи загрузки ожидается один путь {key}.")
    return rows[0][0]


def atomic_write(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".imx296-", delete=False) as f:
        tmp = Path(f.name)
        try:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def build_overlay(work, port):
    source = HERE / f"q6a-{port}-innomaker-imx296.dts"
    expanded = work / source.name
    overlay = expanded.with_suffix(".dtbo")
    subprocess.run(["cpp", "-nostdinc", "-undef", "-P", "-x", "assembler-with-cpp",
                    source, "-o", expanded], check=True)
    # The CAM1 fragment contains only port@0. Its parent has more ports in the base DTB.
    subprocess.run(["dtc", "-@", "-Wno-graph_child_address", "-I", "dts", "-O", "dtb",
                    "-o", overlay, expanded], check=True)
    return overlay


def read_default(esp, stock, token):
    loader = esp / "loader/loader.conf"
    lines = loader.read_bytes().decode().splitlines(keepends=True) if loader.exists() else []
    rows = fields(lines, "default")
    if not rows:
        normal = re.compile(re.escape(token) + r"-\d[\w.+-]*\.conf")
        if any(entry != stock and not normal.fullmatch(entry.name) for entry in stock.parent.glob("*.conf")):
            raise ValueError("В EFI несколько записей и default не задан. Нельзя безопасно определить конфигурацию.")
        return stock, lines
    if len(rows) != 1 or len(rows[0]) != 1:
        raise ValueError(f"Неоднозначное значение default в {loader}.")
    name = rows[0][0].removesuffix(".conf")
    if Path(name).name != name or not name:
        raise ValueError(f"Недопустимое имя записи: {name}")
    entry = stock.with_name(name + ".conf")
    if not entry.is_file():
        raise ValueError(f"Не удалось однозначно определить текущую запись по default {name}.")
    return entry, lines


def loader_config(esp, entry, lines):
    # embloader builds its menu IDs without .conf; systemd-boot uses the filename.
    if not fields(lines, "default"):
        return "".join(lines).encode()
    efis = [esp / p for p in ("EFI/systemd/systemd-bootaa64.efi", "EFI/BOOT/BOOTAA64.EFI")]
    kinds = set()
    for path in efis:
        if path.is_file():
            data = path.read_bytes()
            if re.search(rb"\(embloader 0\.(?:4|7)(?:[.) ])", data):
                kinds.add("embloader")
            elif b"#### LoaderInfo: systemd-boot " in data or b"#### LoaderInfo: systemd " in data:
                if b"(embloader " not in data:
                    kinds.add("systemd-boot")
                else:
                    kinds.add("unknown")
            else:
                kinds.add("unknown")
    if kinds not in ({"embloader"}, {"systemd-boot"}):
        raise ValueError("Не удалось однозначно определить загрузчик EFI. Конфигурация сохранена без изменений.")
    desired = entry.stem if kinds == {"embloader"} else entry.name
    return replace_field(lines, "default", desired)


def replace_field(lines, key, value):
    data = "".join(lines)
    if fields(lines, key) == [value.split()]:
        return data.encode()
    result = []
    inserted = False
    for line in lines:
        if line.split()[:1] == [key]:
            if not inserted:
                result.append(f"{key} {value}\n")
                inserted = True
        else:
            result.append(line)
    if not inserted:
        if result and not result[-1].endswith("\n"):
            result.append("\n")
        result.append(f"{key} {value}\n")
    return "".join(result).encode()


def write_if_changed(path, data, backup=False):
    before = path.read_bytes() if path.exists() else None
    if before == data:
        return False
    saved = path.with_name(path.name + ".before-imx296")
    if backup and before is not None and not saved.exists():
        atomic_write(saved, before)
    atomic_write(path, data)
    return True


def bound_peripherals(dt_root, buses):
    devices = {}
    for bus in ("i2c", "spi", "mipi-dsi"):
        for dev in (buses / bus / "devices").glob("*"):
            node = (dev / "of_node").resolve()
            if (dev / "driver").exists() and node.is_relative_to(dt_root) and (node / "compatible").is_file():
                devices["/" + str(node.relative_to(dt_root))] = (
                    (node / "compatible").read_bytes().rstrip(b"\0").decode().split("\0"))
    return devices


def verify_peripherals(tree, devices):
    checked = set()
    for node, compatible in devices.items():
        try:
            same = output("fdtget", tree, node, "compatible").split() == compatible
        except subprocess.CalledProcessError:
            same = False
        if not same:
            raise ValueError(f"В итоговом DTB отсутствует работающее устройство {node} ({compatible[0]}).")
        path = PurePosixPath(node)
        for parent in (path, *path.parents):
            if parent not in checked:
                status = output("fdtget", "-d", "okay", tree, str(parent), "status")
                if status not in ("ok", "okay"):
                    raise ValueError(f"Итоговый DTB отключает работающее устройство {node} через {parent}.")
                checked.add(parent)


def install(esp, token, kernel, work, port, modules_file, devices):
    if not token or Path(token).name != token or token == "..":
        raise ValueError("Некорректный идентификатор в /etc/kernel/entry-token.")
    images = efi_file(esp, f"/{token}/{kernel}")
    catalog = images / "dtbo"
    stock = esp / f"loader/entries/{token}-{kernel}.conf"
    entry, loader_lines = read_default(esp, stock, token)
    if entry.is_symlink() or not entry.is_file():
        raise ValueError(f"Отсутствует исходная загрузочная запись: {entry}")
    lines = entry.read_bytes().decode().splitlines(keepends=True)
    base = efi_file(esp, single_path(lines, "devicetree"))
    linux = efi_file(esp, single_path(lines, "linux"))
    if not (linux.is_relative_to(images) and linux.is_file()
            and "radxa,dragon-q6a" in output("fdtget", base, "/", "compatible").split()):
        raise ValueError(f"{entry.name} должна указывать на ядро {kernel} и DTB Dragon Q6A.")
    loader = esp / "loader/loader.conf"
    next_loader = loader_config(esp, entry, loader_lines)
    built = {p: build_overlay(work, p) for p in PORTS}
    name = built[port].name
    enabled_camera = catalog / name
    inactive_camera = catalog / (name + ".disabled")
    selected = next((p for p in (enabled_camera, inactive_camera) if p.is_file()), built[port])
    camera = "/" + enabled_camera.relative_to(esp).as_posix()
    old = [p for row in fields(lines, "devicetree-overlay") for p in row]
    # Overlays following the IMX296 may reference symbols it introduces.
    before = old[:old.index(camera)] if camera in old else old
    current = base
    if before:
        current = work / "before-camera.dtb"
        subprocess.run(["fdtoverlay", "-i", base, "-o", current,
                        *(efi_file(esp, p) for p in before)], check=True)
    bus_symbol, phy_index = PORTS[port]
    bus = output("fdtget", current, "/__symbols__", bus_symbol)
    phy = output("fdtget", current, "/__symbols__", "camss") + f"/ports/port@{phy_index}"
    sensor = bus + "/camera@1a"
    tx, rx = sensor + "/port/endpoint", phy + "/endpoint"

    def linked(tree):
        return (output("fdtget", tree, sensor, "compatible") == "sony,imx296"
                and output("fdtget", tree, rx, "remote-endpoint") == output("fdtget", tree, tx, "phandle")
                and output("fdtget", tree, tx, "remote-endpoint") == output("fdtget", tree, rx, "phandle"))

    occupied = (any(n.endswith("@1a") for n in output("fdtget", "-l", current, bus).split())
                or any(n.split("@")[0] == "endpoint" for n in output("fdtget", "-l", current, phy).split()))
    wanted = list(old)
    if occupied:
        try:
            existing = linked(current)
        except subprocess.CalledProcessError:
            existing = False
        if not existing:
            raise ValueError(f"{port.upper()} занят другой конфигурацией камеры. Установка остановлена до записи.")
        # A custom base or another overlay already provides the complete route.
    elif camera not in wanted:
        wanted.append(camera)
    merged = current
    if camera in wanted:
        merged = work / "camera.dtb"
        subprocess.run(["fdtoverlay", "-i", base, "-o", merged,
                        *(selected if p == camera else efi_file(esp, p) for p in wanted)], check=True)
        if not linked(merged):
            raise ValueError(f"Проверка связи {port.upper()} с CSIPHY{phy_index} не прошла.")

    verify_peripherals(merged, devices)
    next_entry = (replace_field(lines, "devicetree-overlay", " ".join(wanted))
                  if wanted != old else "".join(lines).encode())
    files = {}
    for p, blob in built.items():
        enabled = catalog / blob.name
        inactive = enabled.with_suffix(".dtbo.disabled")
        if p == port and camera in wanted:
            files[enabled] = selected.read_bytes()
        elif not enabled.exists() and not inactive.exists():
            files[inactive] = blob.read_bytes()
    # Every prerequisite is published before the entry referencing it. If interrupted
    # at any point, the previous or new entry is usable and the install can be retried.
    catalog.mkdir(exist_ok=True)
    changed = False
    for path, data in files.items():
        if write_if_changed(path, data) and path == catalog / name:
            changed = True
    config = modules_file.read_bytes() if modules_file.exists() else b""
    missing = [m for m in MODULES if m.encode() not in config.splitlines()]
    if missing:
        separator = b"\n" if config and not config.endswith(b"\n") else b""
        write_if_changed(modules_file, config + separator + ("\n".join(missing) + "\n").encode(), backup=True)
    if write_if_changed(entry, next_entry, backup=True):
        changed = True
    if (next_loader or loader.exists()) and write_if_changed(loader, next_loader, backup=True):
        changed = True
    if enabled_camera in files and inactive_camera.exists() and inactive_camera.read_bytes() == files[enabled_camera]:
        inactive_camera.unlink()
    return entry, changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=str.lower, choices=PORTS, default="cam1",
                        help="разъём IMX296 (по умолчанию cam1/J14)")
    args = parser.parse_args()
    if sys.platform != "linux" or os.geteuid() != 0:
        parser.exit(1, "Запустите на Q6A: sudo python3 install.py\n")
    dt_root = Path("/sys/firmware/devicetree/base")
    if b"radxa,dragon-q6a" not in (dt_root / "compatible").read_bytes().split(b"\0"):
        raise ValueError("Ожидается плата Radxa Dragon Q6A.")
    if not ESP.is_mount():
        raise ValueError("EFI System Partition не смонтирован в /boot/efi.")
    kernel = os.uname().release
    token = Path("/etc/kernel/entry-token").read_text().strip()
    import fcntl  # Linux target only.
    with open("/run/lock/q6a-imx296.lock", "a") as lock, tempfile.TemporaryDirectory() as work:
        fcntl.flock(lock, fcntl.LOCK_EX)
        dependencies()
        for module in MODULES:
            subprocess.run(["modprobe", module], check=True)
        entry, changed = install(ESP, token, kernel, Path(work), args.port,
                                 Path("/etc/modules-load.d/q6a-imx296.conf"),
                                 bound_peripherals(dt_root, Path("/sys/bus")))
    print(f"IMX296 {args.port.upper()}: {entry.name}")
    if not changed:
        from capture import find_camera
        try:
            media, sensor = find_camera(args.port, f"msm_csiphy{PORTS[args.port][1]}")
        except (ValueError, subprocess.SubprocessError) as error:
            bus = (dt_root / "__symbols__" / PORTS[args.port][0]).read_bytes().rstrip(b"\0").decode()
            node = dt_root / bus.lstrip("/") / "camera@1a/compatible"
            if node.exists() and b"sony,imx296" in node.read_bytes().split(b"\0"):
                print(f"Оверлей уже загружен. Захват пока недоступен.\n{error}")
                return
        else:
            print(f"Камера доступна: {media}, {sensor}. Можно запускать capture.py.")
            return
    print("При следующей обычной перезагрузке настройки вступят в силу: sudo reboot")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
