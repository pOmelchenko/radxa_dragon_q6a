"""Prepare pinned Android XBL and a reproducible SPI image from Radxa files."""
from pathlib import Path
import os
import platform
import re
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zlib

from . import files, prepare_xbl


def number(expression, sectors):
    """The pinned XML uses integers and NUM_DISK_SECTORS subtraction only."""
    if re.fullmatch(r'\d+\.?', expression):
        return int(expression.rstrip('.'))
    match = re.fullmatch(r'NUM_DISK_SECTORS-(\d+)\.?', expression)
    if match:
        return sectors - int(match[1])
    raise ValueError(f'Unsupported pinned XML expression: {expression}')


def check_gpt(image):
    sectors = len(image) // 4096
    tables = []
    for lba, alternate in ((1, sectors - 1), (sectors - 1, 1)):
        header = bytearray(image[lba * 4096:(lba + 1) * 4096])
        prepare_xbl.require(header[:8] == b'EFI PART', 'Missing SPI GPT header')
        size, crc = struct.unpack_from('<II', header, 12)
        prepare_xbl.require(92 <= size <= 4096, 'Invalid SPI GPT header size')
        struct.pack_into('<I', header, 16, 0)
        prepare_xbl.require(zlib.crc32(header[:size]) == crc, 'Invalid SPI GPT header CRC')
        current, backup, first, last = struct.unpack_from('<QQQQ', header, 24)
        prepare_xbl.require((current, backup) == (lba, alternate), 'Invalid SPI GPT locations')
        prepare_xbl.require(6 <= first <= last < sectors - 5, 'Invalid SPI GPT usable range')
        at, count, entry_size, entries_crc = struct.unpack_from('<QIII', header, 72)
        offset, length = at * 4096, count * entry_size
        prepare_xbl.require(entry_size >= 128 and 0 < length <= 16384 and offset + length <= len(image), 'Invalid SPI GPT array')
        entries = image[offset:offset + length]
        prepare_xbl.require(zlib.crc32(entries) == entries_crc, 'Invalid SPI GPT entries CRC')
        for i in range(count):
            entry = entries[i * entry_size:(i + 1) * entry_size]
            if any(entry[:16]):
                low, high = struct.unpack_from('<QQ', entry, 32)
                prepare_xbl.require(first <= low <= high <= last, 'SPI partition out of range')
        tables.append(entries)
    prepare_xbl.require(tables[0] == tables[1], 'SPI GPT arrays differ')


def build_spi(directory, patched_xbl):
    """Build 32 MiB with zero-filled unused space; apply only DISK XML patches."""
    directory = Path(directory)
    image = bytearray(33554432)
    sectors = len(image) // 4096
    occupied = []
    names = []
    for node in ET.parse(directory / 'rawprogram0.xml').getroot().iter('program'):
        a = node.attrib
        prepare_xbl.require(int(a['SECTOR_SIZE_IN_BYTES']) == 4096 and int(a['physical_partition_number']) == 0,
                            'Unexpected SPI sector size or LUN')
        prepare_xbl.require(a['file_sector_offset'] == '0' and a['sparse'] == 'false', 'Unexpected SPI image format')
        path = files.contained_file(directory, a['filename'])
        content = patched_xbl if path.name == 'xbl.elf' else path.read_bytes()
        start = number(a['start_sector'], sectors) * 4096
        end = start + int(a['num_partition_sectors']) * 4096
        prepare_xbl.require(0 <= start < end <= len(image) and len(content) <= end - start, 'SPI payload out of bounds')
        prepare_xbl.require(all(end <= low or start >= high for low, high in occupied), 'Overlapping SPI payloads')
        occupied.append((start, end))
        names.append(path.name)
        image[start:start + len(content)] = content
    prepare_xbl.require(sorted(names) == ['gpt_backup0.bin', 'gpt_main0.bin', 'xbl.elf'], 'Unexpected SPI payload list')
    for node in ET.parse(directory / 'patch0.xml').getroot().iter('patch'):
        a = node.attrib
        if a['filename'] != 'DISK':
            continue
        prepare_xbl.require(int(a['SECTOR_SIZE_IN_BYTES']) == 4096 and int(a['physical_partition_number']) == 0,
                            'Unexpected SPI patch target')
        offset = number(a['start_sector'], sectors) * 4096 + int(a['byte_offset'])
        size = int(a['size_in_bytes'])
        prepare_xbl.require(size in (4, 8) and 0 <= offset <= len(image) - size, 'SPI patch out of bounds')
        match = re.fullmatch(r'CRC32\(([^,]+),(\d+)\)', a['value'])
        if match:
            start, length = number(match[1], sectors) * 4096, int(match[2])
            prepare_xbl.require(0 <= start and 0 < length <= len(image) - start, 'SPI CRC range out of bounds')
            value = zlib.crc32(image[start:start + length])
        else:
            value = number(a['value'], sectors)
        image[offset:offset + size] = value.to_bytes(size, 'little')
    check_gpt(image)
    return bytes(image)


def normalize_metadata(data):
    """The pinned Windows mke2fs ignores fake time; fix times without checksums."""
    image = bytearray(data)
    prepare_xbl.require(len(image) == 16777216, 'Unexpected metadata size')
    prepare_xbl.require(struct.unpack_from('<H', image, 1024 + 56)[0] == 0xef53, 'Not an ext filesystem')
    features = struct.unpack_from('<III', image, 1024 + 92)
    prepare_xbl.require(features == (0x2c, 0x42, 0x7b), 'Unexpected ext4 features; timestamp normalization requires no metadata/inode checksums')
    inodes, blocks = struct.unpack_from('<II', image, 1024)
    prepare_xbl.require(inodes == blocks == 4096 and struct.unpack_from('<I', image, 1024 + 24)[0] == 2,
                        'Unexpected metadata geometry')
    prepare_xbl.require(struct.unpack_from('<H', image, 1024 + 88)[0] == 256, 'Unexpected inode size')
    inode_table = struct.unpack_from('<I', image, 4096 + 8)[0] * 4096
    prepare_xbl.require(inode_table == 16384, 'Unexpected inode table location')
    epoch = 1700000000
    for offset in (48, 64, 264):  # s_wtime, s_lastcheck, s_mkfs_time
        struct.pack_into('<I', image, 1024 + offset, epoch)
    # Only these reserved/root/journal/lost+found inodes carry creation times.
    for inode in (1, 2, 8, 11):
        start = inode_table + (inode - 1) * 256
        for offset in (8, 12, 16, 144):  # atime, ctime, mtime, crtime
            if struct.unpack_from('<I', image, start + offset)[0]:
                struct.pack_into('<I', image, start + offset, epoch)
    return bytes(image)


def build_metadata(mke2fs, lock):
    mke2fs = Path(mke2fs).resolve()
    prepare_xbl.require(mke2fs.is_file(), 'Missing mke2fs executable')
    config = files.contained_file(mke2fs.parent, 'mke2fs.conf')
    if platform.system() == 'Windows':
        files.check_entries(mke2fs.parent, lock['metadata_builder']['windows_files'])
        prepare_xbl.require(mke2fs.name == 'mke2fs.exe', 'Use the pinned Android SDK mke2fs.exe')
    env = dict(os.environ, MKE2FS_CONFIG=str(config))
    with tempfile.TemporaryDirectory(prefix='q6a-metadata-') as temp:
        path = Path(temp) / 'metadata-ext4.img'
        subprocess.run([str(mke2fs), '-t', 'ext4', '-b', '4096', '-I', '256', '-m', '0',
                        '-U', 'a2d5f74f-7273-47f6-9cab-75667326ff01', '-E',
                        'hash_seed=a2d5f74f-7273-47f6-9cab-75667326ff02,lazy_itable_init=0,lazy_journal_init=0',
                        '-F', str(path), '4096'], env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=True)
        data = normalize_metadata(path.read_bytes())
    expected = lock['metadata_image']
    prepare_xbl.require(len(data) == expected['bytes'] and prepare_xbl.sha(data) == expected['sha256'],
                        'Generated metadata differs from pinned ext4 image')
    return data


def prepare(directory, output_dir, mke2fs):
    import json
    lock = files.load_json(files.ROOT / 'firmware/android15-ufs-toshiba512/files.lock.json')
    count = files.check_entries(directory, lock['files'])
    spec = files.load_json(files.ROOT / 'firmware/android15-ufs-toshiba512/xbl-patch.json')
    directory, output_dir = Path(directory), Path(output_dir)
    original = (directory / 'spinor/xbl.elf').read_bytes()
    xbl, checked = prepare_xbl.patch_xbl(original, spec)
    spi = build_spi(directory / 'spinor', xbl)
    prepare_xbl.require(prepare_xbl.sha(spi) == lock['reproducible_spi_sha256'], 'SPI differs from pinned build')
    metadata = build_metadata(mke2fs, lock)
    outputs = {'xbl-ufs30-power-test.elf': xbl, 'spi-android-toshiba512.bin': spi,
               'metadata-ext4.img': metadata}
    report = {'release': lock['release'], 'device_contacted': False, 'source_files_checked': count,
              'checked_sha384_segments': checked, 'spi_gpt_crcs_verified': True, 'unused_spi_fill': 0,
              'vendor_signature_valid': False,
              'files': {name: {'bytes': len(data), 'sha256': prepare_xbl.sha(data)} for name, data in outputs.items()}}
    outputs['prepared.json'] = (json.dumps(report, indent=2) + '\n').encode('utf-8')
    for name, data in outputs.items():
        path = output_dir / name
        prepare_xbl.require(not path.is_symlink() and (not path.exists() or path.read_bytes() == data), f'Existing output differs: {path}')
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        (output_dir / name).write_bytes(data)
    return report
