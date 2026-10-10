# Radxa Dragon Q6A Source Documents

Collected on **2026-09-23** from the
[official resource catalog](https://docs.radxa.com/en/dragon/q6a/download)
and Radxa's documentation repository. Original downloads are retained without
conversion. Interpretation lives in the [hardware reference](../research/hardware-reference.md),
[system/storage notes](../research/system-and-storage.md) and
[camera investigation](../camera-research.md).

## Retained Originals

| File | Revision and scope |
| --- | --- |
| [Schematic](radxa-q6a-schematic-v1.21.pdf) | **V1.21**, 35 PDF pages. Reviewed schematic title blocks carry **2025-09-12**; internal printed sheet numbers run within a 37-sheet scheme and differ from PDF page numbers. |
| [Component placement](radxa-q6a-components-v1.21.pdf) | Published as **V1.21**, two pages: top and bottom. PDF creation/modification metadata date is **2025-06-21**. |
| [2D dimensions](radxa-q6a-dimensions-v1.21.pdf) | Published as **V1.21**, one page with both board faces. PDF creation/modification metadata date is **2025-09-15**. |
| [Interface illustration](interfaces.webp) | Numbered board interfaces from the pinned documentation repository. No explicit image revision; use as an orientation aid. |

The schematic review covered the block diagram, debug UART and camera
circuits. Both placement pages, the dimensions and interface illustration
were visually inspected. Retaining the entire schematic is not a complete
electrical audit; the owner's PCB revision and fitted optional parts still
need identification. Metadata dates are not inferred publication dates.

## Online And Pinned Sources

Radxa documentation was inspected at repository commit
[`c44bfe6c70845dd265b50436a6b3a52f0d107377`](https://github.com/radxa-docs/docs/tree/c44bfe6c70845dd265b50436a6b3a52f0d107377/i18n/en/docusaurus-plugin-content-docs/current/dragon/q6a)
(committer timestamp **2026-09-22T03:42:06Z**). The manifest records raw-source
paths, URLs, sizes and hashes. Upstream Markdown was read in a temporary
checkout area and is not duplicated here with unresolved imports/asset paths.
Wrapper pages are identified as such; their imported common guides were not
audited as full procedures.

- [Board overview](https://docs.radxa.com/en/dragon/q6a),
  [hardware interfaces](https://docs.radxa.com/en/dragon/q6a/hardware-use/hardware-info),
  [CSI](https://docs.radxa.com/en/dragon/q6a/hardware-use/mipi-csi),
  [GPIO](https://docs.radxa.com/en/dragon/q6a/hardware-use/pin-gpio),
  [power](https://docs.radxa.com/en/dragon/q6a/hardware-use/power-header) and
  [debug UART](https://docs.radxa.com/en/dragon/q6a/system-config/uart-debug).
- [NVMe](https://docs.radxa.com/en/dragon/q6a/hardware-use/nvme),
  [eMMC/UFS](https://docs.radxa.com/en/dragon/q6a/hardware-use/ufs-emmc-com),
  [boot options](https://docs.radxa.com/en/dragon/q6a/hardware-use/boot),
  [BIOS recovery](https://docs.radxa.com/en/dragon/q6a/low-level-dev/spi-fw) and
  [Radxa OS boot configuration](https://docs.radxa.com/en/dragon/q6a/low-level-dev/radxa-os-boot).
- [Android installation](https://docs.radxa.com/en/dragon/q6a/other-system/android),
  [Radxa's Armbian guide](https://docs.radxa.com/en/dragon/q6a/other-system/armbian),
  [Armbian's current Q6A catalog](https://armbian.com/boards/radxa-dragon-q6a),
  [Camera 4K example](https://docs.radxa.com/en/dragon/q6a/accessories/camera-4k)
  and [FAQ](https://docs.radxa.com/en/dragon/q6a/faq).

Image and firmware archives are linked through the resource catalog, **not
downloaded or inspected internally**. No image hash, flashing success or
hardware support is inferred from a filename. Armbian's catalog was read
online; OS-image checksum/signature validation remains an installation step.

Additional mechanical resources, **not downloaded or reviewed**:
[2D DXF archive](https://dl.radxa.com/dragon/q6a/hw/radxa_dragon_q6a_2d_dxf_v1.21.zip)
and [3D STEP archive](https://dl.radxa.com/dragon/q6a/hw/radxa_dragon_q6a_3d_stp_v1.21.zip).

## Provenance And Verification

[sources.json](sources.json) records URLs, retrieval date, revisions, sizes,
page counts and SHA-256 values. [SHA256SUMS](SHA256SUMS) covers the **four local
originals**. From this directory:

```sh
sha256sum -c SHA256SUMS
```

Hashes identify the retrieved bytes; they are not publisher signatures.
Original documents retain their publishers' ownership and notices. Temporary
PDF text/raster extractions are not included in this package.
