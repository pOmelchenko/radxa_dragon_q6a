#!/usr/bin/env python3
"""Capture one free-running Y10P frame from the IMX296 on Q6A CAM2."""
import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import mkdtemp

WIDTH, HEIGHT = 1456, 1088


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def find_camera():
    # Match the immutable sensor -> CSIPHY2 link, including its actual I2C bus.
    for media in sorted(Path("/dev").glob("media[0-9]*")):
        graph = subprocess.check_output(["media-ctl", "-d", media, "-p"], text=True)
        for entity in graph.split("- entity ")[1:]:
            sensor = re.match(r"\d+: (imx296 \d+-001a) \(", entity)
            if sensor and re.search(r'-> "msm_csiphy2":0 \[ENABLED\b', entity):
                return media, sensor[1]
    raise ValueError("В media graph нет связи imx296 → msm_csiphy2. Проверьте probe и порт J16.")


def format_value(description, field, pattern):
    match = re.search(rf"^\s*{field}\s*:\s*({pattern})", description, re.MULTILINE)
    if not match:
        raise ValueError(f"Не удалось прочитать {field} из v4l2-ctl.")
    return match[1]


def capture():
    os.environ["LC_ALL"] = "C"
    media, sensor = find_camera()
    ctl = ["media-ctl", "-d", media]
    print(f"{media}: {sensor} → msm_csiphy2 → msm_csid0 → msm_vfe0_rdi0", flush=True)
    run(*ctl, "-l", '"msm_csiphy2":1 -> "msm_csid0":0 [1]')
    run(*ctl, "-l", '"msm_csid0":1 -> "msm_vfe0_rdi0":0 [1]')
    for entity, pad in [(sensor, 0), ("msm_csiphy2", 0), ("msm_csid0", 0),
                        ("msm_csid0", 1), ("msm_vfe0_rdi0", 0)]:
        run(*ctl, "-V", f'"{entity}":{pad} [fmt:Y10_1X10/{WIDTH}x{HEIGHT} field:none]')

    video = subprocess.check_output([*ctl, "-e", "msm_vfe0_video0"], text=True).strip()
    v4l2 = ["v4l2-ctl", "-d", video]
    run(*v4l2, f"--set-fmt-video=width={WIDTH},height={HEIGHT},pixelformat=Y10P")
    fmt = subprocess.check_output([*v4l2, "--get-fmt-video"], text=True)
    print(video, fmt, sep="\n", flush=True)
    if (format_value(fmt, "Pixel Format", r"'[^']+'") != "'Y10P'" or
            format_value(fmt, "Width/Height", r"\d+/\d+") != f"{WIDTH}/{HEIGHT}"):
        raise ValueError("CAMSS согласовал другой формат или размер кадра.")
    stride = int(format_value(fmt, "Bytes per Line", r"\d+"))
    size = int(format_value(fmt, "Size Image", r"\d+"))
    row_bytes = WIDTH * 5 // 4
    if stride < row_bytes or size < stride * HEIGHT:
        raise ValueError(f"Некорректные параметры буфера: stride={stride}, sizeimage={size}.")

    output = Path(mkdtemp(prefix="imx296-", dir="."))
    raw = output / "frame.raw"
    print(f"Захват в {output.resolve()}", flush=True)
    run(*v4l2, "--stream-mmap=4", "--stream-count=1", f"--stream-to={raw}", timeout=15)
    frame = raw.read_bytes()
    if len(frame) != size:
        raise ValueError(f"Получено {len(frame)} байт, ожидалось {size}.")

    # In MIPI RAW10 each fifth byte holds the low two bits of four pixels.
    with (output / "preview.pgm").open("wb") as preview:
        preview.write(f"P5\n{WIDTH} {HEIGHT}\n255\n".encode("ascii"))
        for y in range(HEIGHT):
            row = bytearray(frame[y * stride:y * stride + row_bytes])
            del row[4::5]
            preview.write(row)
    print(f"RAW10 и 8-битное превью сохранены в {output.resolve()}")


if __name__ == "__main__":
    try:
        capture()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
