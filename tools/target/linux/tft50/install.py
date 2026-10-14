#!/usr/bin/env python3
"""Plan/install TFT50 files for one EFI entry, or restore its saved transaction."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
DEPENDENCY = HERE.parents[2] / 'dependencies/linux-tft50'
ESP = Path('/boot/efi')
DISPLAY = 'q6a-btt-tft50-display.dtbo'
POWER = 'q6a-btt-tft50-power.dtbo'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    require(not path.is_symlink(), f'Symlink is not accepted: {path}')
    return sha(path.read_bytes()) if path.exists() else None


def command(*args):
    return subprocess.check_output([str(arg) for arg in args], text=True).strip()


def efi_path(esp, name):
    parts = PurePosixPath(name).parts
    require(name.startswith('/') and '..' not in parts and '\\' not in name,
            f'Invalid EFI path: {name}')
    path = esp / name.lstrip('/')
    require(path.resolve().is_relative_to(esp.resolve()), f'Path escapes EFI: {name}')
    return path


def entry_fields(text):
    fields = {}
    for index, line in enumerate(text.splitlines()):
        words = line.split()
        if not words or words[0].startswith('#'):
            continue
        fields.setdefault(words[0], []).append((index, words[1:]))
    return fields


def one_field(fields, key):
    matches = fields.get(key, [])
    require(len(matches) == 1 and len(matches[0][1]) == 1,
            f'Expected one {key} path in EFI entry')
    return matches[0][1][0]


def rewrite_entry(text, stock, display, power):
    fields = entry_fields(text)
    overlays = fields.get('devicetree-overlay', [])
    require(len(overlays) <= 1, 'Expected at most one devicetree-overlay line')
    index, paths = overlays[0] if overlays else (None, [])
    require(paths.count(stock) <= 1 and len(paths) == len(set(paths)),
            'Duplicate overlays in EFI entry')
    require(not any(Path(p).name in (DISPLAY, POWER) for p in paths),
            'TFT50 overlays are already present; use the existing installation')
    lines = text.splitlines(keepends=True)
    updated = [display if p == stock else p for p in paths]
    if stock not in paths:
        updated.append(display)
    updated.append(power)
    overlay_line = 'devicetree-overlay ' + ' '.join(updated) + '\n'
    if index is None:
        if lines and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        lines.append(overlay_line)
    else:
        lines[index] = overlay_line
    return ''.join(lines), paths


def atomic_write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def stage_transaction(changes, backup, preserved, kernel, expected=None):
    """Save every before/after payload before the first system-file change."""
    require(len(changes) == len({str(path) for path, _ in changes}), 'Duplicate target')
    backup.mkdir(mode=0o700)
    records = []
    for index, (path, after) in enumerate(changes):
        require(not path.is_symlink(), f'Symlink is not accepted: {path}')
        before = path.read_bytes() if path.exists() else None
        before_hash = sha(before) if before is not None else None
        if expected is not None:
            require(before_hash == expected[str(path)], f'Target changed since planning: {path}')
        mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
        # VFAT permissions come from mount options; chmod may be unsupported.
        if path.is_relative_to(ESP):
            mode = None
        before_name = f'{index}.before' if before_hash is not None else None
        after_name = f'{index}.after' if after is not None else None
        if before_name:
            (backup / before_name).write_bytes(before)
        if after_name:
            (backup / after_name).write_bytes(after)
        records.append({'path': str(path), 'before': before_name, 'after': after_name,
                        'before_sha256': before_hash,
                        'after_sha256': sha(after) if after is not None else None,
                        'mode': mode})
    manifest = {'schema_version': 1, 'kernel_release': kernel, 'files': records,
                'preserved': preserved}
    (backup / 'transaction.json').write_text(json.dumps(manifest, indent=2) + '\n')
    shutil.copyfile(Path(__file__), backup / 'install.py')
    return manifest


def verify_preserved(manifest):
    for name, expected in manifest['preserved'].items():
        require(file_hash(Path(name)) == expected, f'Preserved file changed: {name}')


def apply_transaction(backup):
    manifest = json.loads((backup / 'transaction.json').read_text())
    verify_preserved(manifest)
    for record in manifest['files']:
        require(file_hash(Path(record['path'])) == record['before_sha256'],
                f'Target changed since planning: {record["path"]}')
        if record['after']:
            require(sha((backup / record['after']).read_bytes()) == record['after_sha256'],
                    'Corrupt staged payload')
    for record in manifest['files']:
        path = Path(record['path'])
        if record['after'] is None:
            path.unlink()
        else:
            atomic_write(path, (backup / record['after']).read_bytes(), record['mode'])
    verify_preserved(manifest)


def rollback_transaction(backup):
    manifest = json.loads((backup / 'transaction.json').read_text())
    # Check all targets before touching any: never overwrite a later user edit.
    for record in manifest['files']:
        require(file_hash(Path(record['path'])) in
                (record['before_sha256'], record['after_sha256']),
                f'File changed after installation; inspect manually: {record["path"]}')
        if record['before']:
            require(sha((backup / record['before']).read_bytes()) == record['before_sha256'],
                    'Corrupt rollback payload')
    for record in reversed(manifest['files']):
        path = Path(record['path'])
        if record['before'] is None:
            path.unlink(missing_ok=True)
        else:
            atomic_write(path, (backup / record['before']).read_bytes(), record['mode'])
    return manifest['kernel_release']


def plan_install(build, entry):
    lock = json.loads((DEPENDENCY / 'source.lock.json').read_text())
    kernel = lock['kernel_release']
    require(platform.release() == kernel, f'Qualified kernel required: {kernel}')
    require(b'radxa,dragon-q6a' in Path('/sys/firmware/devicetree/base/compatible').read_bytes().split(b'\0'),
            'This installer requires a Radxa Dragon Q6A')
    require(ESP.is_mount(), 'The EFI system partition must be mounted at /boot/efi')
    require(entry.parent == ESP / 'loader/entries' and entry.suffix == '.conf',
            'Select an entry directly under /boot/efi/loader/entries')
    require(not entry.name.startswith('Q6A-before-'), 'A recovery entry cannot be the install target')
    require(not entry.is_symlink(), 'EFI entry must not be a symlink')
    old_bytes = entry.read_bytes()
    old = old_bytes.decode()
    fields = entry_fields(old)
    linux = one_field(fields, 'linux')
    base_rel = one_field(fields, 'devicetree')
    require(kernel in PurePosixPath(linux).parts and kernel in PurePosixPath(base_rel).parts,
            'Entry must reference the running kernel and its own DTB directory')
    require(efi_path(ESP, linux).is_file(), 'EFI kernel image is missing')
    base = efi_path(ESP, base_rel)
    stock_rel = str(PurePosixPath(base_rel).parent / 'dtbo' / lock['stock_overlay']['filename'])
    stock = efi_path(ESP, stock_rel)
    display_rel = str(PurePosixPath(stock_rel).parent / DISPLAY)
    power_rel = str(PurePosixPath(stock_rel).parent / POWER)
    new, paths = rewrite_entry(old, stock_rel, display_rel, power_rel)
    stock_active = stock_rel in paths
    if stock_active:
        require(file_hash(stock) == lock['stock_overlay']['sha256'], 'Unexpected active stock overlay')
    preserved = {str(base): file_hash(base)}
    for path in paths:
        if path != stock_rel:
            other = efi_path(ESP, path)
            preserved[str(other)] = file_hash(other)
            exclusive = subprocess.run(['fdtget', '-t', 's', str(other), '/metadata', 'exclusive'],
                                       capture_output=True, text=True)
            require(not {'mdss_dsi', 'gpio80'}.intersection(exclusive.stdout.split()),
                    f'Another overlay owns DSI or GPIO80: {path}')
    require(all(preserved.values()), 'Missing base DTB or other active overlay')
    build_manifest = json.loads((build / 'build.json').read_text())
    require(build_manifest['kernel_release'] == kernel and
            build_manifest['source_lock_sha256'] == file_hash(DEPENDENCY / 'source.lock.json') and
            build_manifest['driver_sha256'] == lock['patches'][-1]['result_sha256'],
            'Build manifest does not match this pinned source/kernel')
    names = ('edt-ft5x06.ko', DISPLAY, POWER)
    payloads = {name: (build / name).read_bytes() for name in names}
    for name, data in payloads.items():
        require(sha(data) == build_manifest['files'][name], f'Build file changed: {name}')
    require(sha(payloads[DISPLAY]) == lock['display_overlay_sha256'] and
            sha(payloads[POWER]) == lock['power_overlay_sha256'], 'Unexpected TFT50 overlays')
    require(command('modinfo', '-F', 'vermagic', build / names[0]).split()[0] == kernel,
            'Module vermagic does not match kernel')
    module_root = Path('/lib/modules') / kernel
    selected = Path(command('modinfo', '-n', 'edt_ft5x06'))
    require(selected.parent == module_root / 'kernel/drivers/input/touchscreen',
            f'A module override is already installed: {selected}')
    initrd = Path('/boot') / f'initrd.img-{kernel}'
    initrd_listing = command('lsinitramfs', initrd)
    require(not any('edt-ft5x06.ko' in p or 'edt_ft5x06.ko' in p
                    for p in initrd_listing.splitlines()),
            'edt-ft5x06 is embedded in initramfs; this recipe does not cover that case')

    with tempfile.TemporaryDirectory(prefix='q6a-tft50-check-') as temp:
        merged = Path(temp) / 'merged.dtb'
        ordered = [build / DISPLAY if p == stock_rel else efi_path(ESP, p) for p in paths]
        if not stock_active:
            ordered.append(build / DISPLAY)
        command('fdtoverlay', '-i', base, '-o', merged, *ordered, build / POWER)
        bus = command('fdtget', '-t', 's', merged, '/__symbols__', 'i2c13')
        props = command('fdtget', '-p', merged, bus + '/touch-controller@38').split()
        require('interrupts' not in props and 'interrupt-parent' not in props,
                'Touch IRQ remains in the merged tree')
        tlmm = command('fdtget', '-t', 's', merged, '/__symbols__', 'tlmm')
        for child in command('fdtget', '-l', merged, tlmm).split():
            node = tlmm + '/' + child
            props = command('fdtget', '-p', merged, node).split()
            if 'gpio-hog' in props and child != 'btt-tft50-lcd-power-hog':
                gpios = command('fdtget', '-t', 'u', merged, node, 'gpios').split()
                require('80' not in gpios[::2], 'Another GPIO hog already owns GPIO80')

    module = module_root / 'updates/q6a-tft50/edt-ft5x06.ko'
    disabled = Path(str(stock) + '.disabled')
    recovery = entry.parent / 'Q6A-before-tft50.conf'
    recovery_lines = old.splitlines(keepends=True)
    if stock_active:
        overlay_index = fields['devicetree-overlay'][0][0]
        recovery_lines[overlay_index] = 'devicetree-overlay ' + ' '.join(
            p + '.disabled' if p == stock_rel else p for p in paths) + '\n'
    titles = fields.get('title', [])
    require(len(titles) == 1, 'Expected one title in EFI entry')
    recovery_lines[titles[0][0]] = 'title Q6A before TFT50 installation\n'
    changes = [(efi_path(ESP, display_rel), payloads[DISPLAY]),
               (efi_path(ESP, power_rel), payloads[POWER]), (module, payloads[names[0]]),
               (recovery, ''.join(recovery_lines).encode())]
    if stock_active:
        changes.append((disabled, stock.read_bytes()))
    for path, _ in changes:
        require(not path.exists() and not path.is_symlink(), f'Target already exists: {path}')
    if stock_active:
        changes.append((stock, None))
    changes.append((entry, new.encode()))
    require(entry.read_bytes() == old_bytes, 'EFI entry changed while preparing plan')
    expected = {str(path): None for path, _ in changes}
    expected[str(entry)] = sha(old_bytes)
    if stock_active:
        expected[str(stock)] = lock['stock_overlay']['sha256']
    return changes, preserved, kernel, module, expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--entry', type=Path, help='Explicit current-kernel EFI entry')
    parser.add_argument('--apply', action='store_true', help='Install; otherwise only validate and print')
    parser.add_argument('--rollback', type=Path, help='Restore a saved transaction directory')
    args = parser.parse_args()
    try:
        require(os.geteuid() == 0, 'Run with sudo on the Q6A (EFI files require root even for a plan)')
        if args.rollback:
            require(not (args.build or args.entry or args.apply), 'Use --rollback by itself')
            kernel = rollback_transaction(args.rollback.resolve())
            command('depmod', '-a', kernel)
            os.sync()
            print('Saved files restored. Reboot to apply; the loaded module was not changed.')
            return
        require(args.build and args.entry, 'Both --build and --entry are required')
        changes, preserved, kernel, module, expected = plan_install(args.build.resolve(), args.entry.absolute())
        print(json.dumps({'kernel': kernel, 'changes': [str(p) for p, _ in changes],
                          'preserved_sha256': preserved, 'apply': args.apply}, indent=2))
        if not args.apply:
            return
        # mkdtemp reserves a unique name; staging requires an empty, new directory.
        backup = Path(tempfile.mkdtemp(prefix='q6a-tft50-', dir='/var/backups'))
        backup.rmdir()
        stage_transaction(changes, backup, preserved, kernel, expected)
        print(f'Backup: {backup}', flush=True)
        os.sync()
        try:
            apply_transaction(backup)
            command('depmod', '-a', kernel)
            require(Path(command('modinfo', '-n', 'edt_ft5x06')) == module,
                    'depmod did not select the installed module')
        except Exception:
            rollback_transaction(backup)
            command('depmod', '-a', kernel)
            os.sync()
            raise
        os.sync()
        print(f'Installed for next boot. Rollback: sudo python3 {backup}/install.py --rollback {backup}')
        print('The running module and live device tree were not changed. Reboot when ready.')
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
