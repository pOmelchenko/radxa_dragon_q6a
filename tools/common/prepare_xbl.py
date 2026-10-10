"""Reproduce the exact tested XBL/SPI candidate. No USB or board access."""
from pathlib import Path
import argparse
import hashlib
import json
import struct

REPO = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def patch_xbl(original, spec):
    require(sha(original) == spec['source_xbl_sha256'], 'Unexpected source XBL SHA256')
    require(original[:4] == b'\x7fELF' and original[4:6] == b'\x02\x01', 'Expected ELF64 little endian')
    header = struct.unpack_from('<HHIQQQIHHHHHH', original, 16)
    require(header[1] == 183, 'Expected AArch64 ELF')
    phoff, phsize, phnum = header[4], header[8], header[9]
    require(phsize == 56, 'Unexpected ELF program header size')
    segments = [struct.unpack_from('<IIQQQQQQ', original, phoff+i*phsize) for i in range(phnum)]
    hashseg, codeseg = segments[1], segments[2]
    hashoff, hashsize = hashseg[2], hashseg[5]
    codeoff, codesize = codeseg[2], codeseg[5]
    digest = hashlib.sha384(original[codeoff:codeoff+codesize]).digest()
    table = original[hashoff:hashoff+hashsize]
    require(table.count(digest) == 1, 'Code digest not unique in hash table')
    digestoff = hashoff + table.find(digest)
    require(digestoff == int(spec['sha384_code_digest_offset'], 0), 'Unexpected code digest offset')
    tableoff = digestoff - 2*48

    def validate_hashes(image):
        checked = []
        for i, segment in enumerate(segments):
            if i == 1 or segment[5] == 0:
                continue
            off, size = segment[2], segment[5]
            require(off+size <= len(image), f'Segment {i} out of bounds')
            expected = hashlib.sha384(image[off:off+size]).digest()
            require(image[tableoff+i*48:tableoff+(i+1)*48] == expected, f'Bad segment hash {i}')
            checked.append(i)
        return checked

    validate_hashes(original)
    instruction = spec['instruction']
    offset = int(instruction['file_offset'], 0)
    oldword = int(instruction['before_word'], 0)
    newword = int(instruction['after_word'], 0)
    require(struct.unpack_from('<I', original, offset)[0] == oldword, 'Unexpected original instruction')
    candidate = bytearray(original)
    struct.pack_into('<I', candidate, offset, newword)
    candidate[digestoff:digestoff+48] = hashlib.sha384(candidate[codeoff:codeoff+codesize]).digest()
    checked = validate_hashes(candidate)
    changes = {i for i, (a,b) in enumerate(zip(original,candidate)) if a != b}
    require(changes <= set(range(offset,offset+4)) | set(range(digestoff,digestoff+48)), 'Unexpected bytes changed')
    require(len(changes) == spec['changed_bytes'] and len(candidate) == len(original), 'Unexpected patch extent')
    require(sha(candidate) == spec['patched_xbl_sha256'], 'Patched XBL does not match tested candidate')
    return bytes(candidate), checked


def patch_spi(original_spi, original_xbl, patched_xbl, spec):
    require(len(original_spi) == 32*1024*1024, 'SPI must be exactly 32 MiB')
    require(sha(original_spi) == spec['source_spi_sha256'], 'Unexpected source SPI SHA256')
    start = spec['spi_xbl_lba'] * spec['spi_sector_bytes']
    end = start + len(original_xbl)
    require(original_spi[start:end] == original_xbl, 'Original SPI XBL differs from source ELF')
    candidate = original_spi[:start] + patched_xbl + original_spi[end:]
    require(len(candidate) == len(original_spi), 'SPI size changed')
    require(sha(candidate) == spec['patched_spi_sha256'], 'Patched SPI does not match tested candidate')
    return candidate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xbl', type=Path, required=True)
    parser.add_argument('--spi', type=Path, help='Exact original Android 32 MiB SPI backup')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    spec = json.loads((REPO/'firmware/android15-ufs-toshiba512/xbl-patch.json').read_text(encoding='utf-8'))
    original = args.xbl.read_bytes()
    xbl, checked = patch_xbl(original, spec)
    outputs = {'xbl-ufs30-power-test.elf': xbl}
    if args.spi:
        outputs['spi-android-ufs30-power-test.bin'] = patch_spi(args.spi.read_bytes(), original, xbl, spec)
    report = {
        'device_contacted': False,
        'vendor_signature_valid': False,
        'hashes_match_tested_candidates': True,
        'checked_sha384_segments': checked,
        'changed_xbl_bytes': spec['changed_bytes'],
        'files': {name: {'bytes':len(data), 'sha256':sha(data)} for name,data in outputs.items()},
    }
    outputs['rebuild.json'] = (json.dumps(report,indent=2)+'\n').encode('utf-8')
    # Validate every output before writing; preserve any differing prior output.
    for name,data in outputs.items():
        target = args.output_dir/name
        require(not target.exists() or target.read_bytes() == data, f'Existing output differs: {target}')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name,data in outputs.items():
        (args.output_dir/name).write_bytes(data)
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
