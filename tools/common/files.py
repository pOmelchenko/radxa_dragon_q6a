"""Verify pinned firmware files without opening a USB device."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def contained_file(root, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError(f'Invalid relative file path: {name!r}')
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != name:
        raise ValueError(f'Invalid relative file path: {name!r}')
    root = Path(root).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f'Missing file or path outside package: {name}')
    return path


def check_entries(root, entries):
    if not isinstance(entries, list) or not entries:
        raise ValueError('Expected a nonempty file list')
    names = set()
    for entry in entries:
        name = entry['path']
        if name in names:
            raise ValueError(f'Duplicate package entry: {name}')
        names.add(name)
        expected = entry['sha256']
        size = entry['bytes']
        if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
            raise ValueError(f'Invalid SHA256: {name}')
        if type(size) is not int or size < 0:
            raise ValueError(f'Invalid file size: {name}')
        path = contained_file(root, name)
        if path.stat().st_size != size or digest(path) != expected:
            raise ValueError(f'File size or SHA256 mismatch: {name}')
    return len(entries)


def verify_bundle(bundle):
    bundle = Path(bundle).resolve()
    lock = load_json(ROOT / 'firmware/android15-ufs-toshiba512/bundle.lock.json')
    manifest = contained_file(bundle, 'manifest.json')
    if digest(manifest) != lock['manifest_sha256']:
        raise ValueError('Bundle manifest differs from the pinned SHA256')
    data = load_json(manifest)
    if data.get('board_serial') != '7B57A3EB' or data.get('chip') != 'THGJFCT2T84BAKCB':
        raise ValueError('Bundle targets a different board or UFS model')
    if len(data['files']) != lock['frozen_files']:
        raise ValueError('Bundle file count differs from the pinned package')
    count = check_entries(bundle, data['files'])
    profiles = load_json(ROOT / 'firmware/bios-profiles.json')['profiles']
    check_entries(bundle, [
        {'path': value['bundle_path'], 'bytes': value['bytes'], 'sha256': value['sha256']}
        for value in profiles.values()
    ])
    return {'files_checked': count, 'device_contacted': False}


def verify_linux_bios(directory):
    data = load_json(ROOT / 'firmware/linux-bios/files.lock.json')
    return {'files_checked': check_entries(directory, data['files']), 'device_contacted': False}
