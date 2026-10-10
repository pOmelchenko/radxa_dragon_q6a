# Q6A Systems, Storage And Recovery

Status and official sources checked on **2026-09-23**. These are preparation
notes, not a performed installation or recovery report.

## Current System And Intended Use

The owner reports **Ubuntu on a 512 GB NVMe SSD, 12 GB RAM**. The board is
intended to control the scanner, with **headless Armbian** replacing Ubuntu.
An eMMC/UFS Android installation is a separate experiment under consideration.
Ubuntu release/image origin, kernel, BIOS, PCB/silicon revision and SSD model
remain unknown; do not label this installation Radxa OS without evidence.

Before changing storage or firmware, collect a baseline **on the Q6A**:

```sh
cat /etc/os-release
uname -a
free -h
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL
findmnt /
sudo dmidecode -s bios-version
```

Keep the image filename/hash, partition layout, BIOS identification and PCB
markings with the eventual experiment report. Back up the current NVMe and
retain a recovery image before replacing it. RAM capacity alone is not a
record of the silicon variant or the appropriate firmware.

## Headless Armbian Plan

The [Armbian Q6A catalog](https://armbian.com/boards/radxa-dragon-q6a), inspected
on this date, labels the board **Standard** and lists **Armbian 26.8.1** stable
Minimal/CLI images with **current 6.18.2**, including **Debian 13 Trixie** and
**Ubuntu 26.04 Resolute**. Separate UFS variants are listed. These are dated
catalog observations; no image was downloaded, installed or tested here.

Select a **Minimal/CLI image for Q6A and the intended storage**, preserving
the filename and publisher checksum/signature. The Debian stable Minimal
entry is a reasonable first candidate; Ubuntu Minimal is also available if
its userspace is preferred. Neither needs a desktop. The
[Radxa Armbian page](https://docs.radxa.com/en/dragon/q6a/other-system/armbian)
still lists different distribution releases, so use Armbian's own catalog
for the image selection. Radxa also requires current UEFI firmware; resolve
the concrete compatible version before installation.

Proposed migration sequence:

1. Preserve the Ubuntu/NVMe baseline and a matching Linux BIOS recovery bundle.
2. Test the selected image on spare boot media, where supported, before
   overwriting the 512 GB drive. Confirm its firmware and storage requirements.
3. Configure network access and SSH for unattended boot. Verify access after
   power cycling with no HDMI display or graphical login. For Wi-Fi, use a
   system connection that does not depend on unlocking a desktop keyring.
4. Validate NVMe detection/root filesystem, Ethernet, thermal behavior and
   sustained file writes. Keep test files on a filesystem; do not use a raw
   disk overwrite as a storage benchmark.
5. Move to the intended NVMe installation and repeat cold-boot checks. Start
   [AR0234 bring-up](../camera-research.md#ar0234-experiment) against the exact
   installed kernel/device tree before claiming camera support.

The distribution label does not qualify CSI, ISP, encoder, GPIO or timestamp
behavior. Record those separately. Scanner deployment belongs to its product;
this package owns board preparation and independent peripheral tests.

## Storage And Published Images

| Medium | Linux role | Published Android 15 route |
| --- | --- | --- |
| Current 512 GB NVMe | Main planned Armbian storage; M.2 2230 PCIe Gen3 x2 | Not a supported system boot medium in Radxa's inspected Android guide. |
| Radxa-compatible eMMC | Alternative system medium | Matching eMMC image plus the accompanying SPI NOR BIOS. |
| Radxa-compatible UFS | Alternative system medium with storage-specific images | Matching UFS image plus SPI NOR BIOS and additional UFS provisioning. |
| microSD / USB | Linux installation/recovery candidates | Not listed as Android system boot media. |

The [combo connector](https://docs.radxa.com/en/dragon/q6a/hardware-use/ufs-emmc-com)
accepts eMMC **or** UFS. Buy a Q6A-compatible module rather than choosing by
capacity or storage-standard name alone. Neither module has been selected.
For a first Android boot experiment, eMMC has fewer setup steps; UFS is useful
if evaluating that storage path is itself a goal. This is a workflow comparison,
not a measured performance ranking or a purchase decision.

The [Radxa download catalog](https://docs.radxa.com/en/dragon/q6a/download)
lists Radxa OS R2 `output_512` images for SD/USB/eMMC/NVMe and `output_4096`
for UFS. Its R1-and-newer requirement is BIOS **20251230 or newer**; the listed
Linux BIOS bundle is **flat_build_260120**. These Radxa OS identifiers do not
identify the owner's Ubuntu or replace Armbian's firmware requirements.

For Android, the catalog currently links **20260630-b1 Android 15** archives
for eMMC and UFS. Each contains its matching BIOS. The overview also mentions
Android 16 for ES silicon, while other overview text mentions Android 14;
the concrete download/install path reviewed here is Android 15. Confirm the
actual CS/ES unit and image applicability before flashing.

## Android Experiment And Return To Linux

The [Android guide](https://docs.radxa.com/en/dragon/q6a/other-system/android)
requires an x86 Windows/Linux host, a compatible module and the Qualcomm
tools obtained through Software Center/account access. Its published image
workflow uses **xPCATApp**:

1. Enter EDL by holding the EDL button while applying board power, then
   releasing it. Connect the host with the specified Type-A data cable to
   the board's **USB 3.1 OTG port**, not the USB-C power input.
2. Flash the archive's `spinor` directory as **SPINOR**.
3. For UFS only, provision with `provision_ufs31.xml` and the matching
   `prog_firehose_ddr.elf` device programmer.
4. Flash `emmc/asic` as **EMMC**, or `ufs/asic` as **UFS**.

Use the linked guide and matching bundle for the actual procedure. Generic
Linux image-writing or BIOS EDL-NG instructions do not establish an alternative
supported Android flashing method. UFS provisioning changes the module's
configuration and belongs to a deliberate reinstall, not a harmless probe.

**The SPI NOR BIOS is shared board state.** A separate Android module does
not isolate the NVMe system from firmware changes. Retain the known-working
Linux BIOS/image and verify the documented EDL connection before changing it.
When returning to Linux, restore a compatible BIOS if required, select the
intended boot medium and recheck NVMe boot. Automatic dual boot and return
without reflashing are not established by these sources.

The [direct-UFS boot option](https://docs.radxa.com/en/dragon/q6a/hardware-use/boot)
is a separate resistor modification that removes SD/eMMC/NVMe boot support.
**It is not a step in the BIOS-plus-UFS Android procedure above.** Keep the
default SPI NOR boot arrangement for this planned NVMe/Android experiment.

For Linux firmware recovery, Radxa documents
[BIOS flashing through EDL-NG](https://docs.radxa.com/en/dragon/q6a/low-level-dev/spi-fw).
Record the exact loader, rawprogram/patch files and destination memory type.
Do not erase working BIOS as routine preparation. The
[serial-console reference](hardware-reference.md#power-and-serial-console)
provides a separate way to capture boot failures.

## BSP And Camera Boundary

Radxa's [kernel-development entry](https://docs.radxa.com/en/dragon/q6a/low-level-dev/build-system/kernel)
points to `radxa-pkg/linux-qcom`. Its
[Radxa OS boot guide](https://docs.radxa.com/en/dragon/q6a/low-level-dev/radxa-os-boot)
describes BIOS/default DT versus explicit device trees and overlays. Do not
assume Radxa OS `rsetup`, boot paths or overlays apply unchanged to Armbian.

Radxa's [Camera 4K example](https://docs.radxa.com/en/dragon/q6a/accessories/camera-4k)
uses libcamera/GStreamer and distinguishes software and Venus hardware
encoding. It does not establish AR0234 support. The
[FAQ](https://docs.radxa.com/en/dragon/q6a/faq) also records a hypervisor-related
encoder workaround and its effect on `/dev/mtd0`; treat it as a BSP-specific
diagnostic reference, not a setting to apply preemptively.

Android boot success would likewise not prove AR0234 camera HAL/ISP support.
Keep Linux and Android camera results separate. Source revision, file hashes
and retrieved manufacturer documents are indexed in [docs](../docs/README.md).
