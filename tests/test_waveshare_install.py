"""Boot-entry and failed-install regression tests for the Q6A panel installer."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "tools/target/linux/waveshare-35h/install.py"
SPEC = importlib.util.spec_from_file_location("waveshare_install", SOURCE)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)

KERNEL = "7.0.11-7-qcom"
DIR = "/RadxaOS/" + KERNEL
BASE = (f"title Ubuntu\nlinux {DIR}/linux\ninitrd {DIR}/initrd\n"
        f"devicetree {DIR}/qcs6490-radxa-dragon-q6a.dtb\noptions root=UUID=test rw\n")


class BootEntryTests(unittest.TestCase):
    def test_preserve_cameras_and_remove_tft50_pair_from_trial(self):
        old = BASE + (f"devicetree-overlay {DIR}/ar0234.dtbo {DIR}/q6a-btt-tft50-display.dtbo\n"
                      f"devicetree-overlay {DIR}/q6a-btt-tft50-power.dtbo {DIR}/imx519.dtbo\n")
        text, _, new, kept, removed = installer.trial_entry(old, KERNEL)
        self.assertEqual(kept, [f"{DIR}/ar0234.dtbo", f"{DIR}/imx519.dtbo"])
        self.assertEqual(len(removed), 2)
        self.assertNotIn("btt-tft50", text)
        self.assertIn("options root=UUID=test rw\n", text)
        self.assertIn(f"title {installer.TITLE}\n", text)
        self.assertTrue(text.endswith("devicetree-overlay " + " ".join([*kept, new]) + "\n"))

    def test_stock_entry_without_overlays_and_without_trailing_newline(self):
        text, _, new, kept, _ = installer.trial_entry(BASE.rstrip(), KERNEL)
        self.assertEqual(kept, [])
        self.assertEqual(new, f"{DIR}/dtbo/q6a-waveshare-35h.dtbo")
        self.assertIn("rw\n", text)
        self.assertTrue(text.endswith("devicetree-overlay " + new + "\n"))

    def test_wrong_kernel_and_parent_path(self):
        with self.assertRaises(ValueError):
            installer.trial_entry(BASE, "6.18.2-3-qcom")
        with self.assertRaises(ValueError):
            installer.efi_file(Path("esp"), "/RadxaOS/../../outside")

    def test_pulse_trial_preserves_options_and_uses_same_overlay(self):
        original = BASE.replace("rw", 'rw label="two words" -- rescue') + f"devicetree-overlay {DIR}/imx519.dtbo\n"
        pulse, _, overlay, kept, _ = installer.trial_entry(original, KERNEL, sync_pulse=True)
        event, _, baseline, baseline_kept, _ = installer.trial_entry(original, KERNEL)
        self.assertEqual((overlay, kept), (baseline, baseline_kept))
        self.assertIn(f"title {installer.PULSE_TITLE}\n", pulse)
        self.assertIn(f'options {installer.PULSE_ARG} root=UUID=test rw label="two words" -- rescue\n', pulse)
        self.assertNotIn("sync_pulse", event)
        with self.assertRaisesRegex(ValueError, "original"):
            installer.trial_entry(pulse, KERNEL)

    def test_pulse_trial_without_options_or_with_a_conflicting_setting(self):
        original = BASE.split("options")[0].rstrip()
        pulse, *_ = installer.trial_entry(original, KERNEL, sync_pulse=True)
        self.assertIn(f"\noptions {installer.PULSE_ARG}\n", pulse)
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            installer.trial_entry(BASE.replace("rw", "rw panel-waveshare-35h.sync_pulse=0"),
                                  KERNEL, sync_pulse=True)


class PublishTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.module = root / installer.MODULE
        self.overlay = root / installer.OVERLAY
        self.entry = root / "trial.conf"
        self.data = (b"module", b"overlay", (installer.MARKER + "\nnew entry\n").encode())

    def install(self):
        installer.publish(self.module, self.overlay, self.entry, self.data, KERNEL)

    def test_depmod_failure_restores_old_module_before_exposing_trial(self):
        self.module.write_bytes(b"old module")
        with patch.object(installer.subprocess, "run",
                          side_effect=[subprocess.CalledProcessError(1, "depmod"), None]) as depmod:
            with self.assertRaises(subprocess.CalledProcessError):
                self.install()
        self.assertEqual(depmod.call_count, 2)
        self.assertEqual(self.module.read_bytes(), b"old module")
        self.assertFalse(self.overlay.exists())
        self.assertFalse(self.entry.exists())

    def test_failed_entry_write_restores_previous_overlay_and_index(self):
        self.overlay.write_bytes(b"old overlay")
        write = installer.atomic_write

        def fail_at_entry(path, data, mode):
            if path == self.entry:
                raise OSError("ESP full")
            write(path, data, mode)

        with patch.object(installer, "atomic_write", side_effect=fail_at_entry), \
                patch.object(installer, "output", return_value=str(self.module)), \
                patch.object(installer.subprocess, "run") as depmod:
            with self.assertRaises(OSError):
                self.install()
        self.assertFalse(self.module.exists())
        self.assertFalse(self.entry.exists())
        self.assertEqual(self.overlay.read_bytes(), b"old overlay")
        self.assertEqual(depmod.call_count, 2)

    def test_repeat_refreshes_index_without_rewriting_payloads(self):
        with patch.object(installer, "output", return_value=str(self.module)), \
                patch.object(installer.subprocess, "run") as depmod:
            self.install()
            with patch.object(installer, "atomic_write") as write:
                self.install()
            write.assert_not_called()
        self.assertEqual(depmod.call_count, 2)
        self.assertEqual(self.entry.read_bytes(), self.data[2])

    def test_foreign_boot_entry_is_preserved(self):
        self.entry.write_bytes(b"manual boot entry")
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(self.entry.read_bytes(), b"manual boot entry")
        self.assertFalse(self.module.exists())
