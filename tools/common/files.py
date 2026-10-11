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


def linux_bios_lock(version):
    folders = {'260120': 'linux-bios', '260916': 'linux-bios-260916'}
    if version not in folders:
        raise ValueError(f'Unsupported pinned Linux BIOS version: {version}')
    return load_json(ROOT / 'firmware' / folders[version] / 'files.lock.json')


def verify_linux_bios(directory, version='260120'):
    data = linux_bios_lock(version)
    return {'version': version, 'files_checked': check_entries(directory, data['files']),
            'device_contacted': False}


def fetch_linux_bios(directory, version='260916'):
    """Fetch the pinned package files; preserve existing files and verify every byte."""
    from urllib.request import urlopen
    if version != '260916':
        raise ValueError('Automatic download is available for BIOS 260916')
    data = linux_bios_lock(version)
    revision = data['source_revision']
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Linux BIOS source must be pinned to a complete Git commit')
    names = set()
    for entry in data['files']:
        name, size, sha256 = entry['path'], entry['bytes'], entry['sha256']
        if not re.fullmatch('[A-Za-z0-9_.-]+', name) or name in ('.', '..') or name in names:
            raise ValueError(f'Invalid or duplicate BIOS filename: {name}')
        if type(size) is not int or not 0 <= size <= 16 * 1024 * 1024:
            raise ValueError(f'Invalid BIOS file size: {name}')
        if not re.fullmatch('[0-9a-f]{64}', sha256):
            raise ValueError(f'Invalid BIOS SHA256: {name}')
        names.add(name)
    if not names:
        raise ValueError('Expected a nonempty BIOS file list')
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    base = f'https://raw.githubusercontent.com/radxa-pkg/edk2-qualcomm/{revision}/src/qcs6490/'
    downloaded = 0
    for entry in data['files']:
        path = directory / entry['path']
        if path.exists() or path.is_symlink():
            check_entries(directory, [entry])
        else:
            with urlopen(base + entry['path'], timeout=40) as response:
                content = response.read(entry['bytes'] + 1)
            if len(content) != entry['bytes'] or hashlib.sha256(content).hexdigest() != entry['sha256']:
                raise ValueError(f'Download size or SHA256 mismatch: {entry["path"]}')
            with path.open('xb') as stream:
                stream.write(content)
            downloaded += 1
        print(f'Verified {entry["path"]}', flush=True)
    result = verify_linux_bios(directory, version)
    result['files_downloaded'] = downloaded
    return result


def verify_linux_image(image, target, uncompressed=False):
    data = load_json(ROOT / 'firmware/radxa-os-r2/images.lock.json')
    candidates = [entry for entry in data['images'] if target in entry['targets']]
    if len(candidates) != 1:
        raise ValueError(f'Expected exactly one pinned Linux image for {target}')
    entry = candidates[0]
    image = Path(image)
    size = entry['uncompressed_bytes' if uncompressed else 'compressed_bytes']
    expected_sha256 = entry['uncompressed_sha256' if uncompressed else 'sha256']
    if not image.is_file() or image.stat().st_size != size:
        raise ValueError(f'Wrong image size for {target}')
    sha256 = hashlib.sha256()
    sha512 = None if uncompressed else hashlib.sha512()
    with image.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            sha256.update(chunk)
            if sha512 is not None:
                sha512.update(chunk)
    if sha256.hexdigest() != expected_sha256 or (sha512 is not None and sha512.hexdigest() != entry['sha512']):
        raise ValueError(f'Wrong image or checksum for {target}')
    result = {'release': data['release'], 'target': target,
              'logical_sector_bytes': entry['logical_sector_bytes'],
              'uncompressed': uncompressed, 'bytes': size,
              'sha256': sha256.hexdigest(), 'device_contacted': False}
    if sha512 is not None:
        result['sha512'] = sha512.hexdigest()
    return result
