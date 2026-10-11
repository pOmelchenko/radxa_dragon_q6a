"""Firmware downloads must verify bytes and preserve existing artifacts."""
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from common import files


class BiosDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'bios'
        self.content = b'verified firmware'
        self.entry = {'path': 'xbl.elf', 'bytes': len(self.content),
                      'sha256': hashlib.sha256(self.content).hexdigest()}
        self.lock = {'source_revision': 'a' * 40, 'files': [self.entry]}
        patch = mock.patch.object(files, 'linux_bios_lock', return_value=self.lock)
        patch.start()
        self.addCleanup(patch.stop)

    def test_corrupt_or_truncated_download_is_not_saved(self):
        for payload in (self.content[:-1], b'X' * len(self.content), self.content + b'!'):
            with self.subTest(payload=payload), mock.patch(
                    'urllib.request.urlopen', return_value=io.BytesIO(payload)):
                with self.assertRaisesRegex(ValueError, 'Download size or SHA256'):
                    files.fetch_linux_bios(self.directory)
                self.assertFalse((self.directory / 'xbl.elf').exists())

    def test_existing_corrupt_file_is_preserved_without_network(self):
        self.directory.mkdir()
        path = self.directory / 'xbl.elf'
        path.write_bytes(b'preserve this backup')
        with mock.patch('urllib.request.urlopen') as request:
            with self.assertRaises(ValueError):
                files.fetch_linux_bios(self.directory)
            request.assert_not_called()
        self.assertEqual(path.read_bytes(), b'preserve this backup')

    def test_matching_cached_file_is_reused_without_network(self):
        self.directory.mkdir()
        (self.directory / 'xbl.elf').write_bytes(self.content)
        with mock.patch('urllib.request.urlopen') as request:
            result = files.fetch_linux_bios(self.directory)
            request.assert_not_called()
        self.assertEqual(result['files_downloaded'], 0)
        self.assertEqual(result['files_checked'], 1)

    def test_download_uses_fixed_repository_and_full_revision(self):
        with mock.patch('urllib.request.urlopen', return_value=io.BytesIO(self.content)) as request:
            result = files.fetch_linux_bios(self.directory)
        request.assert_called_once_with(
            'https://raw.githubusercontent.com/radxa-pkg/edk2-qualcomm/' + 'a' * 40 + '/src/qcs6490/xbl.elf',
            timeout=40)
        self.assertEqual((self.directory / 'xbl.elf').read_bytes(), self.content)
        self.assertEqual(result['files_downloaded'], 1)

    def test_bad_pin_or_escape_path_fails_before_creating_directory(self):
        for revision, name in [('main', 'xbl.elf'), ('a' * 40, '../xbl.elf')]:
            self.lock['source_revision'] = revision
            self.entry['path'] = name
            with self.subTest(revision=revision, name=name), mock.patch('urllib.request.urlopen') as request:
                with self.assertRaises(ValueError):
                    files.fetch_linux_bios(self.directory)
                request.assert_not_called()
                self.assertFalse(self.directory.exists())


if __name__ == '__main__':
    unittest.main()
