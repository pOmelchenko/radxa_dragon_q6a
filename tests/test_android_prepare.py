"""Reject invalid firmware tables before producing a flashable SPI image."""
from pathlib import Path
import struct
import sys
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from common.prepare_android import check_gpt, number, normalize_metadata


def fixture():
    image = bytearray(64 * 4096)
    entries = bytearray(4096)
    entries[:16] = bytes(range(16))
    struct.pack_into('<QQ', entries, 32, 6, 12)
    for lba, alternate, at in [(1, 63, 2), (63, 1, 59)]:
        image[at * 4096:(at + 1) * 4096] = entries
        header = bytearray(4096)
        header[:8] = b'EFI PART'
        struct.pack_into('<III', header, 8, 0x10000, 92, 0)
        struct.pack_into('<QQQQ', header, 24, lba, alternate, 6, 58)
        struct.pack_into('<QIII', header, 72, at, 32, 128, zlib.crc32(entries))
        struct.pack_into('<I', header, 16, zlib.crc32(header[:92]))
        image[lba * 4096:(lba + 1) * 4096] = header
    return image


class AndroidSpiTests(unittest.TestCase):
    def test_both_tables_are_required_and_checked(self):
        check_gpt(fixture())
        for offset in [4096 + 24, 63 * 4096 + 24, 2 * 4096 + 32, 59 * 4096 + 32]:
            image = fixture()
            image[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                check_gpt(image)

    def test_valid_crcs_cannot_hide_disagreeing_tables(self):
        image = fixture()
        image[59 * 4096 + 56] ^= 1
        header_start = 63 * 4096
        struct.pack_into('<I', image, header_start + 88, zlib.crc32(image[59 * 4096:60 * 4096]))
        struct.pack_into('<I', image, header_start + 16, 0)
        struct.pack_into('<I', image, header_start + 16, zlib.crc32(image[header_start:header_start + 92]))
        with self.assertRaisesRegex(ValueError, 'arrays differ'):
            check_gpt(image)

    def test_xml_expressions_are_not_executed(self):
        self.assertEqual(number('NUM_DISK_SECTORS-5.', 8192), 8187)
        for expression in ['__import__("os")', '1+2', '-1', 'NUM_DISK_SECTORS', '1.5']:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                number(expression, 8192)


class MetadataTests(unittest.TestCase):
    def image(self, time):
        data = bytearray(16777216)
        struct.pack_into('<II', data, 1024, 4096, 4096)
        struct.pack_into('<I', data, 1024 + 24, 2)
        struct.pack_into('<H', data, 1024 + 56, 0xef53)
        struct.pack_into('<H', data, 1024 + 88, 256)
        struct.pack_into('<III', data, 1024 + 92, 0x2c, 0x42, 0x7b)
        struct.pack_into('<I', data, 4096 + 8, 4)
        for at in (1024 + 48, 1024 + 64, 1024 + 264, 16384 + 256 + 12):
            struct.pack_into('<I', data, at, time)
        return data

    def test_creation_time_does_not_change_prepared_image(self):
        first = normalize_metadata(self.image(1791717311))
        later = normalize_metadata(self.image(1791717511))
        self.assertEqual(first, later)
        self.assertEqual(normalize_metadata(first), first)

    def test_checksum_features_are_rejected_before_editing(self):
        image = self.image(1791717311)
        struct.pack_into('<I', image, 1024 + 100, 0x7b | 0x400)
        before = bytes(image)
        with self.assertRaisesRegex(ValueError, 'checksums'):
            normalize_metadata(image)
        self.assertEqual(bytes(image), before)


if __name__ == '__main__':
    unittest.main()
