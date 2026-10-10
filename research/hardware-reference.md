# Radxa Dragon Q6A Hardware Reference

Official references inspected on **2026-09-23**. The owner's **12 GB / 512 GB
NVMe** configuration is recorded in the [board inventory](../README.md).
Manufacturer capabilities below are not project test results; match the
actual PCB to the retained **V1.21** documents before wiring.

## Board And Interfaces

![Radxa's numbered connector and component illustration](../docs/interfaces.webp)

Numbers refer to the [official interface description](https://docs.radxa.com/en/dragon/q6a/hardware-use/hardware-info).
The illustration is a vendor reference, not a photograph of the owner's unit.

| Block | Reference capability / practical boundary |
| --- | --- |
| Compute | Qualcomm QCS6490: eight CPU cores, Adreno 643 GPU; LPDDR5. Board-family RAM options do not change the owner's reported 12 GB. |
| Boot firmware (16) | 32 MB QSPI NOR; default boot starts here. OS storage and BIOS are separate. |
| NVMe (3) | M.2 M Key **2230**, **PCIe Gen3 x2**. The owner's 512 GB drive model and measured performance are unknown. |
| Removable storage (12, 23) | microSD and a combo connector for **either eMMC or UFS**. Use a module explicitly compatible with Q6A; this is not a generic phone-storage socket. |
| Network (4, 5, 14, 15) | Gigabit Ethernet; Wi-Fi 6 / Bluetooth 5.4 with external antenna connections; PoE requires a separate HAT. |
| USB (17, 19) | One USB 3.1 Type-A host/OTG port, **lower socket at number 17**; three USB 2.0 Type-A host ports. USB-C (9) is the power input. |
| Display (13, 22) | Four-lane MIPI DSI and HDMI, advertised up to 4K30. Neither is required for the intended steady-state headless service. |
| Expansion (2, 24) | 40-pin GPIO header with multiplexed serial interfaces; RTC battery connector. Pin functions depend on the selected device tree. |
| Mechanical | PCB **85 × 56 mm**, mounting-hole centres **58 × 49 mm**, four **3.5 mm** holes in the retained drawing. Account separately for connectors, SSD, heatsink and cables. |

Sources: [overview](https://docs.radxa.com/en/dragon/q6a),
[NVMe](https://docs.radxa.com/en/dragon/q6a/hardware-use/nvme),
[eMMC/UFS](https://docs.radxa.com/en/dragon/q6a/hardware-use/ufs-emmc-com),
[USB](https://docs.radxa.com/en/dragon/q6a/hardware-use/usb), and
[mechanical drawing](../docs/radxa-q6a-dimensions-v1.21.pdf).

## Camera Connectors

| Connector in V1.21 schematic | Physical interface | Electrical detail to audit |
| --- | --- | --- |
| **J14 / CAM 1** (illustration 11) | **31 pins, 0.3 mm**, four CSI data lanes | I2C and CAM0_POWER_EN pull-ups go to **1.8 V**; reset has a 1.8 V optional pull-up. Both 3.3 V and 5 V supply pins are present. These supply pins do not make the control bus 3.3 V. |
| **J16 / CAM 2**, **J7 / CAM 3** (illustration 25) | **15 pins, 1.0 mm**, two CSI data lanes each; Radxa describes Pi-compatible pinouts | I2C/reset pass through **1.8 V ↔ 3.3 V** translators; connector power is 3.3 V. XCLK routes contain optional resistors, so fitted components and the camera's clock source matter. |

The [CSI guide](https://docs.radxa.com/en/dragon/q6a/hardware-use/mipi-csi)
and schematic **PDF page 32, printed sheet 34/37, CAM** establish these
reference paths. The PDF and printed sheet numbers differ. A module requires
verified pin numbering, contact orientation, supplies, control levels, clock
and CSI routing before any adapter is approved. No AR0234 adapter is specified
by this table; see the [camera experiment](../camera-research.md#ar0234-experiment).

## Power And Serial Console

Radxa recommends a **12 V USB-C PD supply rated at least 2 A**. The alternate
three-pin input is **1 = 12 V, 2 = GND, 3 = PWR**; PWR is a switch input,
not another supply pin. PoE uses the separate expansion arrangement. See the
[power guide](https://docs.radxa.com/en/dragon/q6a/hardware-use/power-header).

For the [debug UART](https://docs.radxa.com/en/dragon/q6a/system-config/uart-debug),
use physical header numbers:

| Board pin | USB-UART adapter connection |
| --- | --- |
| 6, GND | GND |
| 8, board TX | Adapter RX |
| 10, board RX | Adapter TX |

Use **3.3 V TTL**, **115200, 8N1**, no flow control, and the board's own power
supply; leave the adapter's supply wire disconnected. V1.21 schematic PDF
page 24 (printed sheet 26/37) shows `DBG_UART_TX_3V3` / `RX_3V3` at J20 and
translator U47. Radxa's UART page calls this UART0 while its GPIO table labels
pins 8/10 UART5; identify the physical pins and the running OS device rather
than deriving `/dev/tty*` numbering from those names.

The [GPIO table](https://docs.radxa.com/en/dragon/q6a/hardware-use/pin-gpio)
uses Qualcomm GPIO identifiers as well as physical pin numbers. Its example
`/dev/gpiochip4` is not a stable identifier across Ubuntu, Armbian and kernel
versions. Record the actual mapping before peripheral tests.

## Local Drawing Map

- [Schematic](../docs/radxa-q6a-schematic-v1.21.pdf): PDF page 2 block diagram;
  14 eMMC/UFS; 24 GPIO/debug UART; 31 M.2; 32 cameras.
- [Component placement](../docs/radxa-q6a-components-v1.21.pdf): page 1 top,
  page 2 bottom; locate connectors by reference designator and orientation.
- [Dimensions](../docs/radxa-q6a-dimensions-v1.21.pdf): top and bottom layout.
- [Provenance](../docs/README.md): original URLs, revision, retrieval date,
  checksums and review scope.
