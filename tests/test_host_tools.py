"""File-boundary and build-isolation checks on Windows, macOS and Linux."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from common import edl_build, files


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'payload.bin').write_bytes(b'tested payload')
        self.entry = {'path': 'payload.bin', 'bytes': 14,
                      'sha256': hashlib.sha256(b'tested payload').hexdigest()}

    def test_exact_payload_is_accepted(self):
        self.assertEqual(files.check_entries(self.root, [self.entry]), 1)

    def test_corrupt_and_truncated_files_are_rejected(self):
        for data in [b'Tested payload', b'short']:
            with self.subTest(data=data):
                (self.root / 'payload.bin').write_bytes(data)
                with self.assertRaises(ValueError):
                    files.check_entries(self.root, [self.entry])

    def test_unsafe_paths_are_rejected_on_every_os(self):
        for path in ['../payload.bin', '/payload.bin', 'C:/payload.bin',
                     '..\\payload.bin', 'a/../payload.bin', './payload.bin', '']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                files.contained_file(self.root, path)

    def test_duplicate_and_empty_file_lists_are_rejected(self):
        for entries in [[], [self.entry, self.entry]]:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                files.check_entries(self.root, entries)

    def test_bad_metadata_is_rejected(self):
        for changes in [{'bytes': -1}, {'bytes': True}, {'sha256': '0' * 63}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                files.check_entries(self.root, [{**self.entry, **changes}])

    def test_unpinned_bundle_is_rejected_before_reading_manifest_paths(self):
        (self.root / 'manifest.json').write_text(json.dumps({'files': [{'path': '../outside'}]}))
        with self.assertRaisesRegex(ValueError, 'pinned SHA256'):
            files.verify_bundle(self.root)

    def test_symlink_cannot_escape_package(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'outside.bin'
            target.write_bytes(b'outside')
            try:
                (self.root / 'link.bin').symlink_to(target)
            except OSError:
                self.skipTest('Host does not grant symlink creation')
            with self.assertRaises(ValueError):
                files.contained_file(self.root, 'link.bin')


class LinuxImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        entries = []
        self.images = {}
        self.raw_images = {}
        for size, targets in [(512, ['sd', 'nvme']), (4096, ['ufs'])]:
            payload = f'Linux image with {size} byte sectors'.encode()
            path = self.root / f'image-{size}.xz'
            path.write_bytes(payload)
            self.images[size] = path
            raw = b'raw disk data: ' + payload
            raw_path = self.root / f'image-{size}.img'
            raw_path.write_bytes(raw)
            self.raw_images[size] = raw_path
            entries.append({'targets': targets, 'logical_sector_bytes': size,
                            'compressed_bytes': len(payload),
                            'uncompressed_bytes': len(raw),
                            'uncompressed_sha256': hashlib.sha256(raw).hexdigest(),
                            'sha256': hashlib.sha256(payload).hexdigest(),
                            'sha512': hashlib.sha512(payload).hexdigest()})
        self.lock = {'release': 'test', 'images': entries}
        patch = mock.patch.object(files, 'load_json', return_value=self.lock)
        patch.start()
        self.addCleanup(patch.stop)

    def test_ufs_and_standard_images_cannot_be_interchanged(self):
        for target, correct, wrong in [('sd', 512, 4096), ('nvme', 512, 4096), ('ufs', 4096, 512)]:
            with self.subTest(target=target):
                result = files.verify_linux_image(self.images[correct], target)
                self.assertEqual(result['logical_sector_bytes'], correct)
                self.assertFalse(result['device_contacted'])
                with self.assertRaises(ValueError):
                    files.verify_linux_image(self.images[wrong], target)

    def test_corruption_and_incomplete_download_are_rejected(self):
        original = self.images[512].read_bytes()
        for payload in [original[:-1], bytes([original[0] ^ 1]) + original[1:]]:
            with self.subTest(payload=payload):
                self.images[512].write_bytes(payload)
                with self.assertRaises(ValueError):
                    files.verify_linux_image(self.images[512], 'sd')

    def test_ambiguous_and_unknown_targets_are_rejected(self):
        self.lock['images'].append(self.lock['images'][0])
        with self.assertRaises(ValueError):
            files.verify_linux_image(self.images[512], 'sd')
        with self.assertRaises(ValueError):
            files.verify_linux_image(self.images[512], 'unknown')

    def test_raw_images_reject_wrong_sector_type_corruption_and_format(self):
        for target, correct, wrong in [('sd', 512, 4096), ('nvme', 512, 4096), ('ufs', 4096, 512)]:
            with self.subTest(target=target):
                result = files.verify_linux_image(self.raw_images[correct], target, uncompressed=True)
                self.assertTrue(result['uncompressed'])
                with self.assertRaises(ValueError):
                    files.verify_linux_image(self.raw_images[wrong], target, uncompressed=True)
                with self.assertRaises(ValueError):
                    files.verify_linux_image(self.images[correct], target, uncompressed=True)
                with self.assertRaises(ValueError):
                    files.verify_linux_image(self.raw_images[correct], target)
        original = self.raw_images[512].read_bytes()
        for payload in [original[:-1], bytes([original[0] ^ 1]) + original[1:]]:
            self.raw_images[512].write_bytes(payload)
            with self.assertRaises(ValueError):
                files.verify_linux_image(self.raw_images[512], 'sd', uncompressed=True)


class BuildTests(unittest.TestCase):
    def test_native_runtime_detection(self):
        for system, machine, expected in [('Windows', 'AMD64', 'win-x64'),
                                          ('Darwin', 'arm64', 'osx-arm64'),
                                          ('Linux', 'aarch64', 'linux-arm64')]:
            with self.subTest(system=system), mock.patch.object(edl_build.platform, 'system', return_value=system), \
                 mock.patch.object(edl_build.platform, 'machine', return_value=machine):
                self.assertEqual(edl_build.host_runtime(), expected)

    def test_build_plan_pins_source_patch_and_output_runtime(self):
        lock = files.load_json(edl_build.DEPENDENCY / 'source.lock.json')
        with mock.patch.object(edl_build.subprocess, 'run', side_effect=AssertionError('Plan executed a command')):
            for runtime in lock['runtimes']:
                plan = edl_build.build_plan(runtime)
                self.assertIn(lock['base_commit'], plan['commands'][1])
                self.assertIn('--check', plan['commands'][2])
                self.assertIn(runtime, plan['commands'][-1])
                self.assertFalse(plan['device_contacted'])

    def test_different_host_build_stops_before_network(self):
        with mock.patch.object(edl_build, 'host_runtime', return_value='win-x64'), \
             mock.patch.object(edl_build.subprocess, 'run', side_effect=AssertionError('Unexpected network/build')):
            with self.assertRaisesRegex(ValueError, 'current OS'):
                edl_build.build('osx-arm64')

    def test_existing_build_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = {'runtime': 'win-x64', 'source': directory, 'output': directory + '-output'}
            with mock.patch.object(edl_build, 'build_plan', return_value=plan), \
                 mock.patch.object(edl_build, 'host_runtime', return_value='win-x64'), \
                 mock.patch.object(edl_build.subprocess, 'run', side_effect=AssertionError('Existing build touched')):
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    edl_build.build('win-x64')


if __name__ == '__main__':
    unittest.main()
