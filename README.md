# Radxa Dragon Q6A Bring-Up Workspace

Product-independent board references, OS preparation and peripheral experiments
for the Radxa Dragon Q6A. This is an independent
[Git repository](https://github.com/pOmelchenko/radxa_dragon_q6a), also pinned as
a submodule at `hardware/board/radxa_dragon_q6a` in the LiDAR Viewer repository.
Local documents and their provenance are included in this package; links to
shared camera research point to the LiDAR Viewer repository.

## Checkout

To work with this package independently:

```sh
git clone git@github.com:pOmelchenko/radxa_dragon_q6a.git
cd radxa_dragon_q6a
```

Inside an existing LiDAR Viewer checkout, run from its repository root:

```sh
git submodule update --init -- hardware/board/radxa_dragon_q6a
```

Changes to this package belong to its own repository. Publish its commit before
updating the parent repository's gitlink. The initial package was extracted from
[LiDAR Viewer commit `563271b7`](https://github.com/pOmelchenko/lidar_viewer/commit/563271b796e21d1f5a7b39e4457602a4676cac83);
the original manufacturer files and their checksums are preserved.

## Status

Owner report, **2026-09-23**:

| Item | Recorded state |
| --- | --- |
| Board / RAM | Radxa Dragon Q6A, **12 GB RAM**. PCB revision and CS/ES variant not recorded. |
| Storage / current OS | **512 GB NVMe**, currently running **Ubuntu**; distribution release, image source, kernel and BIOS version not recorded. |
| Main direction | Controller for the future scanner; planned migration to **Armbian Minimal/CLI without a desktop**. |
| Camera experiment | The ordered color [AR0234 / DECXIN-3478V1 with 200° lens](https://github.com/pOmelchenko/lidar_viewer/blob/563271b796e21d1f5a7b39e4457602a4676cac83/hardware/camera/ar0234/README.md) was bought for compatibility tests on this board. Delivery and successful capture are not yet recorded. |
| Optional OS experiment | Considering a **Radxa-compatible eMMC or UFS module** for Android; neither purchase nor installation is recorded. |

The installed Ubuntu system is owner-reported hardware state. No reproducible
board test report, camera capture, throughput, synchronization or product
qualification has been added. The intended scanner role does not establish
that a viewer, recorder or SLAM application runs on this board.

## Documentation

- [Original manufacturer documents](docs/README.md): V1.21 schematic,
  component placement, mechanical dimensions and connector illustration,
  with source versions and checksums.
- [Hardware reference](research/hardware-reference.md): storage, CSI ports,
  power, serial console and the relevant schematic pages.
- [Systems, storage and recovery](research/system-and-storage.md): current
  NVMe installation, proposed headless Armbian migration, Android eMMC/UFS
  requirements, BIOS handling and return to Linux.
- [Camera research](camera-research.md): current AR0234 experiment and the
  separate August IMX296 multi-camera proposal, with connector/driver/timing
  boundaries preserved.

## Work To Collect

- PCB/silicon identity, SSD model, OS image, boot firmware and kernel for each
  experiment; retain the current Ubuntu baseline before replacing it.
- Results of headless cold boot, SSH/network recovery and NVMe operation on
  the chosen Armbian image.
- AR0234 module pinout, audited adapter and software port, followed by a
  single-stream test before trigger or multi-camera work.
- Focused Ethernet, Wi-Fi, storage, GPIO, display, or other peripheral checks
  as they are performed.
- Scripts and patches together with their instructions, observed results,
  and remaining limitations.

Add procedures and evidence as experiments are performed. Follow the shared
[hardware ownership and validation rules](https://github.com/pOmelchenko/lidar_viewer/blob/563271b796e21d1f5a7b39e4457602a4676cac83/hardware/README.md).

## Reference Sources

- [Radxa Dragon Q6A product page](https://radxa.com/products/dragon/q6a/)
- [Official board documentation](https://docs.radxa.com/en/dragon/q6a)
- [OS images, boot firmware, and hardware resources](https://docs.radxa.com/en/dragon/q6a/download)
