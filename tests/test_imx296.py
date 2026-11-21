"""Regression coverage for selecting among the three physical Q6A CSI ports."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "tools/target/linux/imx296"
# Physical routing from the Q6A V1.21 and AC008 V1.1 schematics.
ROUTES = (("cam1", "cci0_i2c0", 0, 36), ("cam2", "cci1_i2c0", 2, 77),
          ("cam3", "cci1_i2c1", 3, 78))


def load_script(name):
    spec = importlib.util.spec_from_file_location("imx296_" + name, TOOLS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, "path", [str(TOOLS), *sys.path]):
        spec.loader.exec_module(module)
    return module


class CameraPortsTest(unittest.TestCase):
    def test_detected_but_unlinked_sensor(self):
        capture = load_script("capture")
        graph = "- entity 422: imx296 16-001a (1 pad, 0 link, 0 routes)\n  pad0: Source\n"
        with patch.object(Path, "glob", return_value=[Path("/dev/media0")]), \
                patch.object(subprocess, "check_output", return_value=graph), \
                self.assertRaisesRegex(ValueError, r"imx296 16-001a \(1 pad, 0 link"):
            capture.find_camera("cam1", "msm_csiphy0")

    @unittest.skipUnless(all(shutil.which(c) for c in ("cpp", "dtc", "fdtget")),
                         "Device Tree command-line tools required")
    def test_rsetup_offers_all_ports_and_preserves_selection(self):
        installer = load_script("install")
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            catalog = work / "dtbo"
            catalog.mkdir()
            display = catalog / "btt-tft50.dtbo"
            display.write_bytes(b"display")
            installer.register_overlays(catalog, work)
            for port, bus, _, _ in ROUTES:
                path = catalog / f"q6a-{port}-innomaker-imx296.dtbo.disabled"
                self.assertEqual(installer.output("fdtget", path, "/metadata", "title"),
                                 f"Enable InnoMaker IMX296 Mono on {port.upper()}")
                self.assertEqual(installer.output("fdtget", path, "/metadata", "compatible"), "radxa,dragon-q6a")
                self.assertEqual(installer.output("fdtget", path, "/metadata", "exclusive"), bus)
            active = catalog / "q6a-cam1-innomaker-imx296.dtbo"
            active.with_suffix(".dtbo.disabled").rename(active)
            before = {p.name: p.read_bytes() for p in catalog.iterdir()}
            installer.register_overlays(catalog, work)
            self.assertEqual({p.name: p.read_bytes() for p in catalog.iterdir()}, before)

    def test_capture_routes_only_selected_sensor(self):
        capture = load_script("capture")
        graph = ""
        for num, (_, _, phy, _) in enumerate(ROUTES):
            graph += (f'- entity {num}: imx296 {num}-001a (1 pad, 1 link)\n'
                      f'  pad0: Source\n   -> "msm_csiphy{phy}":0 [ENABLED,IMMUTABLE]\n')
        for num, (port, _, phy, _) in enumerate(ROUTES):
            with self.subTest(port=port), patch.object(Path, "glob", return_value=[Path("/dev/media4")]), \
                    patch.object(subprocess, "check_output", return_value=graph), \
                    patch.object(capture, "run", side_effect=StopIteration) as route, \
                    patch("builtins.print") as message, patch.dict("os.environ"):
                with self.assertRaises(StopIteration):
                    capture.capture(port)
                route.assert_called_once_with("media-ctl", "-d", Path("/dev/media4"), "-l",
                                              f'"msm_csiphy{phy}":1 -> "msm_csid0":0 [1]')
                self.assertIn(f"imx296 {num}-001a → msm_csiphy{phy}", message.call_args.args[0])

    @unittest.skipUnless(all(shutil.which(c) for c in ("cpp", "dtc", "fdtget", "fdtoverlay")),
                         "Device Tree command-line tools required")
    def test_installer_keeps_separate_entries_with_the_right_bus_phy_and_gpio(self):
        installer = load_script("install")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            esp = root / "efi"
            images = esp / "RadxaOS/test-kernel"
            entries = esp / "loader/entries"
            entries.mkdir(parents=True)
            images.mkdir(parents=True)
            base = images / "board.dtb"
            dts = root / "board.dts"
            dts.write_text("""/dts-v1/;
                / {
                    compatible = "radxa,dragon-q6a";
                    tlmm: gpio { gpio-controller; #gpio-cells = <2>; };
                    vreg_l10c_0p88: supply1 {};
                    vreg_l6b_1p2: supply2 {};
                    cci0: cci0 { cci0_i2c0: bus0 {}; };
                    cci1: cci1 { cci1_i2c0: bus0 {}; cci1_i2c1: bus1 {}; };
                    camss: isp { ports { #address-cells = <1>; #size-cells = <0>;
                        port@0 { reg = <0>; }; port@2 { reg = <2>; }; port@3 { reg = <3>; };
                    }; };
                };""")
            subprocess.run(["dtc", "-@", "-o", base, dts], check=True)
            (images / "linux").touch()
            entry = entries / "RadxaOS-test-kernel.conf"
            original = "title Ubuntu\nlinux /RadxaOS/test-kernel/linux\ndevicetree /RadxaOS/test-kernel/board.dtb\n"
            entry.write_text(original)
            for port, bus_symbol, phy, gpio in ROUTES:
                with self.subTest(port=port):
                    trial = installer.install(esp, entry, "test-kernel", root, port)
                    self.assertEqual(trial.name, f"imx296-{port}-{entry.name}")
                    dtb = esp / installer.single_path(trial.read_text().splitlines(), "devicetree").lstrip("/")
                    bus = installer.output("fdtget", dtb, "/__symbols__", bus_symbol)
                    sensor = bus + "/camera@1a"
                    rx = f"/isp/ports/port@{phy}/endpoint"
                    self.assertEqual(installer.output("fdtget", dtb, sensor, "compatible"), "sony,imx296")
                    self.assertEqual(installer.output("fdtget", dtb, rx, "data-lanes"), "0")
                    regulator = f"/regulator-imx296-{port}"
                    self.assertEqual(installer.output("fdtget", "-t", "u", dtb, regulator, "gpio").split()[1:],
                                     [str(gpio), "0"])
                    self.assertEqual(installer.output("fdtget", dtb, sensor, "avdd-supply"),
                                     installer.output("fdtget", dtb, regulator, "phandle"))
            self.assertEqual(entry.read_text(), original)
            self.assertEqual(len(list(entries.glob("imx296-*.conf"))), 3)
