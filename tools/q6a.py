#!/usr/bin/env python3
"""Q6A host tools. File operations and builds only; no automatic flashing."""
import argparse
import json
import subprocess
import sys

from common import check_repository, edl_build, files, prepare_xbl


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check-repo', help='Check documentation, vendor originals and dependency locks')
    bundle = sub.add_parser('verify-bundle', help='Check the exact unpacked Android package')
    bundle.add_argument('--bundle', required=True)
    bios = sub.add_parser('verify-linux-bios', help='Check the Linux BIOS payload files')
    bios.add_argument('--directory', required=True)
    bios.add_argument('--version', choices=['260120', '260916'], default='260120')
    fetch_bios = sub.add_parser('fetch-linux-bios', help='Download and verify pinned BIOS 260916 files')
    fetch_bios.add_argument('--directory', required=True)
    linux_image = sub.add_parser('verify-linux-image', help='Check the pinned Radxa OS image for SD, NVMe or UFS')
    linux_image.add_argument('--image', required=True)
    linux_image.add_argument('--target', required=True, choices=['sd', 'nvme', 'ufs'])
    linux_image.add_argument('--uncompressed', action='store_true', help='Check the extracted raw .img instead of .img.xz')
    xbl = sub.add_parser('prepare-xbl', help='Reproduce the tested XBL and optional full SPI')
    xbl.add_argument('--xbl', required=True)
    xbl.add_argument('--spi')
    xbl.add_argument('--output-dir', required=True)
    edl = sub.add_parser('build-edl', help='Clone, patch, test and build pinned edl-ng sources')
    edl.add_argument('--runtime', default='auto')
    edl.add_argument('--plan', action='store_true', help='Print commands without running them or using the network')
    args = parser.parse_args(argv)
    if args.command == 'check-repo':
        check_repository.main()
        return
    if args.command == 'verify-bundle':
        result = files.verify_bundle(args.bundle)
    elif args.command == 'verify-linux-bios':
        result = files.verify_linux_bios(args.directory, args.version)
    elif args.command == 'fetch-linux-bios':
        result = files.fetch_linux_bios(args.directory)
    elif args.command == 'verify-linux-image':
        result = files.verify_linux_image(args.image, args.target, args.uncompressed)
    elif args.command == 'prepare-xbl':
        options = ['--xbl', args.xbl, '--output-dir', args.output_dir]
        if args.spi:
            options += ['--spi', args.spi]
        prepare_xbl.main(options)
        return
    else:
        runtime = edl_build.host_runtime() if args.runtime == 'auto' else args.runtime
        result = edl_build.build_plan(runtime) if args.plan else edl_build.build(runtime)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
