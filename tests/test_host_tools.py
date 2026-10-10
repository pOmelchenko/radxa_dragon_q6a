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
