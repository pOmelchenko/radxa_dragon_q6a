#!/usr/bin/env python3
"""Build the qualified TFT50 module and overlays, without changing the system."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import urllib.request

HERE = Path(__file__).resolve().parent
DEPENDENCY = HERE.parents[2] / 'dependencies/linux-tft50'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_hash(path, expected):
    require(digest(path) == expected, f'SHA-256 mismatch: {path}')


def run(*args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def build(output, stock_overlay, source=None):
    lock = json.loads((DEPENDENCY / 'source.lock.json').read_text())
    kernel = lock['kernel_release']
    require(platform.system() == 'Linux' and platform.machine() == 'aarch64',
            'Build natively on the Q6A (Linux aarch64)')
    require(platform.release() == kernel, f'Qualified kernel required: {kernel}')
    require(os.geteuid() != 0, 'Build as a normal user, without sudo')
    require(not output.exists(), f'Output already exists: {output}')
    headers = Path('/lib/modules') / kernel / 'build'
    require((headers / 'Makefile').is_file(), f'Install matching kernel headers: {headers}')
    for tool in ('make', 'gcc', 'patch', 'dtc', 'fdtget', 'fdtput', 'modinfo'):
        require(shutil.which(tool), f'Missing tool: {tool}')
    for artifact in [*lock['patches'], lock['license']]:
        check_hash(DEPENDENCY / artifact['path'], artifact['sha256'])
    check_hash(HERE / 'q6a-btt-tft50-power.dts', lock['power_source_sha256'])
    check_hash(stock_overlay, lock['stock_overlay']['sha256'])
    if source:
        check_hash(source, lock['driver']['sha256'])

    output.mkdir(parents=True)
    driver = output / 'edt-ft5x06.c'
    if source:
        shutil.copyfile(source, driver)
    else:
        with urllib.request.urlopen(lock['driver']['url'], timeout=30) as response:
            driver.write_bytes(response.read())
    check_hash(driver, lock['driver']['sha256'])
    shutil.copyfile(driver, output / 'edt-ft5x06-stock.c')
    for patch in lock['patches']:
        run('patch', '--batch', '--forward', '--fuzz=0', f"-p{patch['strip']}",
            '-i', DEPENDENCY / patch['path'], cwd=output)
        check_hash(driver, patch['result_sha256'])
    (output / 'Makefile').write_text('obj-m += edt-ft5x06.o\n')
    with (output / 'build.log').open('w') as log:
        run('make', '-C', headers, f'M={output}', 'CC=gcc', 'modules',
            stdout=log, stderr=subprocess.STDOUT)
    module = output / 'edt-ft5x06.ko'
    vermagic = run('modinfo', '-F', 'vermagic', module,
                   capture_output=True, text=True).stdout.strip()
    require(vermagic.split()[0] == kernel, f'Unexpected module vermagic: {vermagic}')

    power = output / 'q6a-btt-tft50-power.dtbo'
    run('dtc', '-@', '-I', 'dts', '-O', 'dtb', '-o', power,
        HERE / 'q6a-btt-tft50-power.dts')
    check_hash(power, lock['power_overlay_sha256'])
    display = output / 'q6a-btt-tft50-display.dtbo'
    shutil.copyfile(stock_overlay, display)
    node = '/fragment@6/__overlay__/touch-controller@38'
    fixup = run('fdtget', '-t', 's', display, '/__fixups__', 'tlmm',
                capture_output=True, text=True).stdout.strip()
    require(fixup == node + ':interrupt-parent:0', 'Unexpected TLMM fixups in stock overlay')
    for prop in ('interrupts', 'interrupt-parent'):
        run('fdtput', '-d', display, node, prop)
    run('fdtput', '-d', display, '/__fixups__', 'tlmm')
    run('fdtput', '-t', 's', display, '/metadata', 'title',
        'Enable BTT Pi TFT50 V2.1 (I2C touch polling)')
    run('fdtput', '-t', 's', display, '/metadata', 'description',
        'Requires Q6A LCD power companion and polling-enabled edt-ft5x06 module.')
    check_hash(display, lock['display_overlay_sha256'])
    manifest = {
        'kernel_release': kernel, 'vermagic': vermagic,
        'source_lock_sha256': digest(DEPENDENCY / 'source.lock.json'),
        'driver_sha256': digest(driver),
        'compiler': run('gcc', '--version', capture_output=True, text=True).stdout.splitlines()[0],
        'files': {path.name: digest(path) for path in (module, power, display)},
        'system_modified': False,
    }
    (output / 'build.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))
    print(f'Built in {output}; review build.log before installation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New build directory')
    parser.add_argument('--stock-overlay', type=Path, required=True)
    parser.add_argument('--source', type=Path, help='Optional local v7.0.11 driver; hash checked')
    args = parser.parse_args()
    try:
        build(args.output.resolve(), args.stock_overlay.resolve(),
              args.source.resolve() if args.source else None)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
