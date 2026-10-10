# Radxa Dragon Q6A Camera Research

The current experiment is the owner's ordered **color AR0234 with 200° lens**,
bought to test operation on Q6A (owner clarification, **2026-09-23**). The
[board inventory](README.md) records Ubuntu on NVMe and the planned headless
Armbian migration. No successful camera capture, synchronization or sustained
recording result is recorded.

The separate three-IMX296 proposal below is imported from the
[2026-08-21 study](https://github.com/pOmelchenko/lidar_viewer/blob/563271b796e21d1f5a7b39e4457602a4676cac83/docs/raw/research/mobile-usb-gateway-2026-08-21/README.md).
That historical source remains unchanged; it is not the identity of the
camera now ordered for this board.

The [camera catalog](https://github.com/pOmelchenko/lidar_viewer/blob/563271b796e21d1f5a7b39e4457602a4676cac83/hardware/camera/README.md) collects cross-platform research;
the [IMX296 reference](https://github.com/pOmelchenko/lidar_viewer/blob/563271b796e21d1f5a7b39e4457602a4676cac83/hardware/camera/imx296/README.md) owns the shared module,
trigger and optics summary. This page retains Q6A-specific bring-up questions.

## AR0234 Experiment

The [AR0234 package](https://github.com/pOmelchenko/lidar_viewer/blob/563271b796e21d1f5a7b39e4457602a4676cac83/hardware/camera/ar0234/README.md) owns the DECXIN-3478V1 seller
evidence, onsemi documents, 200° optics and
[public driver investigation](https://github.com/pOmelchenko/lidar_viewer/blob/563271b796e21d1f5a7b39e4457602a4676cac83/hardware/camera/ar0234/research/drivers.md).
The module is still recorded as ordered/in transit. Choosing Q6A as the host
does not qualify the module electrically or provide a Q6A driver.

The advertised **22-pin, 0.5 mm, four-lane** module does not directly mate with
Q6A's **31-pin, 0.3 mm, four-lane** connector. Both boards need an audited
pin-to-pin adapter map: CSI data/clock polarity and order, grounds, power,
I2C, reset, power enable, XCLK and cable contact orientation. In particular,
the Q6A V1.21 J14 control-bus pull-ups are **1.8 V**, while its 15-pin camera
ports use **3.3 V** translated controls. A module supply label of 3.3 V does
not establish its I/O voltage. See the
[schematic-derived connector reference](research/hardware-reference.md#camera-connectors).
The two-lane connectors are an alternative only if a compatible module mode,
adapter and driver are established; they cannot deliver four lanes by cable alone.

Radxa's [current CSI list](https://docs.radxa.com/en/dragon/q6a/hardware-use/mipi-csi)
names Camera 4K, 8M 219, 12M 577 and 13M 214, but not AR0234. This is a bounded
support-list observation, not proof that a port is impossible. Existing
Raspberry Pi/Jetson AR0234 drivers are reference implementations; their board
bindings, clocks and capture stacks are not drop-in Q6A support.

Proposed bring-up order:

1. Identify the delivered PCB/module and obtain its readable pinout, electrical
   limits and driver/register material. Establish the adapter before powering it.
2. Record the Q6A OS/kernel/BIOS and device tree. Start with one kernel sensor
   driver, I2C access, regulators/reset/XCLK, and matching CSI/CAMSS endpoints.
3. Prove one conservative capture mode before 120 fps or external trigger:
   frame dimensions, Bayer order/bit depth, exposure/gain, frame sequence,
   CSI errors and sustained file output. Record the userspace/libcamera path.
4. Qualify color processing and 200° fisheye calibration, then the module's
   trigger contract and timestamp behavior. Keep external synchronization
   disconnected until its voltage and timing requirements are established.

Repeat the relevant checks after Ubuntu → Armbian migration: success on one
BSP is not evidence for another. Android would additionally require its
camera HAL/vendor integration and tuning; booting Android or finding a Linux
sensor driver does not supply that stack. The
[OS/storage notes](research/system-and-storage.md) keep this experiment separate
from the optional Android installation.

## Historical IMX296 Connector And Driver Questions

The study identifies two Raspberry Pi-style 15-pin/two-lane connectors and
one Radxa 31-pin/four-lane connector. A third 15-pin IMX296 module needs a
verified adapter for lane, clock, control, reset, power and ground signals;
physical connector compatibility alone does not prove operation.

IMX296 is the sensor investigated; IMX286 is not an alternate spelling. The
August compatible-camera list did not establish IMX296 support. A Linux
sensor driver alone is insufficient: record the kernel/BSP configuration,
device-tree endpoints, regulators, reset/XCLK/I2C, CAMSS and libcamera routing.
Prove one stream before two and three concurrent streams.

## Resource And Timing Proof

For the study's three `1456 x 1088` packed RAW10 active images at 30 fps,
`3 * 1456 * 1088 * 30 * 10 / 8` is about `178.2 MB/s`; at 60 fps it doubles.
These are active-pixel estimates, not measured storage rates. Add alignment,
metadata, buffering and filesystem overhead. The study proposes NVMe or
qualified UFS rather than assuming microSD can sustain that workload.

Retain per-camera frame identity, exposure metadata and loss counters. A common
trigger requires a revision-specific electrical audit; the old Raspberry Pi
GS-camera note mentions a 1.8 V XTR input and an R11 modification on some
revisions. Do not apply that modification without checking the actual module.
Hardware timestamp/PTP behavior on Q6A remains unverified. Record trigger edges,
camera sequences, clock drift and discontinuities before claiming synchronization.

The three-camera lens/yaw arrangement in the source is an application concept,
not a board bring-up requirement. Product calibration, LiDAR alignment and
recording workflow remain separate from this reusable peripheral experiment.

## Sources

- [Original Q6A study](https://github.com/pOmelchenko/lidar_viewer/blob/563271b796e21d1f5a7b39e4457602a4676cac83/docs/raw/research/mobile-usb-gateway-2026-08-21/original-study.md#radxa-dragon-q6a-three-camera-recorder).
- [Radxa CSI documentation](https://docs.radxa.com/en/dragon/q6a/hardware-use/mipi-csi).
- Owner report, 2026-09-23: AR0234 purchased for Q6A compatibility tests;
  Ubuntu/NVMe configuration and planned headless Armbian recorded in the inventory.
- [Retained Radxa schematic V1.21](docs/radxa-q6a-schematic-v1.21.pdf) and
  [manufacturer-source provenance](docs/README.md).
- [Raspberry Pi global-shutter camera](https://www.raspberrypi.com/products/raspberry-pi-global-shutter-camera/).
- [External-trigger documentation](https://www.raspberrypi.com/documentation/accessories/camera.html#external-trigger-on-the-global-shutter-camera).
- [Linux IMX296 driver](https://github.com/torvalds/linux/blob/master/drivers/media/i2c/imx296.c).
