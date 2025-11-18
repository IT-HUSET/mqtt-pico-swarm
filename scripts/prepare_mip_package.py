#!/usr/bin/env python3
"""Convenience wrapper to stage mip files and regenerate manifest/index."""

import argparse
import sys
from pathlib import Path

from build_mip_package import OUTPUT_DEFAULT as BUILD_OUTPUT_DEFAULT
from build_mip_package import main as build_main
from generate_mip_manifest import (
    DEFAULT_BASE_URL,
    DEFAULT_INDEX_OUTPUT,
    DEFAULT_MANIFEST_OUTPUT,
    DEFAULT_MANIFEST_URL,
    DEFAULT_PACKAGE_NAME,
    DEFAULT_STAGING_DIR,
    DEFAULT_SUBDIR,
    main as manifest_main,
)


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="Stage mip files and regenerate manifest")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BUILD_OUTPUT_DEFAULT,
        help="Destination directory for staged mip package (default: build/mip)",
    )
    parser.add_argument(
        "--mpy-cross",
        type=Path,
        help="Optional path to mpy-cross binary for compiling .py files",
    )
    parser.add_argument(
        "--keep-py",
        action="store_true",
        help="Keep .py files when compiling with mpy-cross",
    )
    parser.add_argument(
        "--skip-stage",
        action="store_true",
        help="Skip staging step and only generate manifest/index",
    )
    parser.add_argument(
        "--skip-manifest",
        action="store_true",
        help="Skip manifest/index generation (only stage files)",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=DEFAULT_STAGING_DIR,
        help="Directory containing staged files (default: build/mip)",
    )
    parser.add_argument(
        "--staging-subdir",
        default=DEFAULT_SUBDIR,
        help="Subdirectory inside staging directory to include in manifest",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL where staged files will be hosted (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=DEFAULT_MANIFEST_OUTPUT,
        help=f"Output path for manifest JSON (default: {DEFAULT_MANIFEST_OUTPUT})",
    )
    parser.add_argument(
        "--index-output",
        type=Path,
        default=DEFAULT_INDEX_OUTPUT,
        help=f"Output path for index JSON (default: {DEFAULT_INDEX_OUTPUT}; use --no-index to disable)",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Do not generate index.json",
    )
    parser.add_argument(
        "--manifest-url",
        default=DEFAULT_MANIFEST_URL,
        help=f"Public URL where manifest will be hosted (default: {DEFAULT_MANIFEST_URL})",
    )
    parser.add_argument(
        "--package-name",
        default=DEFAULT_PACKAGE_NAME,
        help=f"Package name for manifest/index (default: {DEFAULT_PACKAGE_NAME})",
    )
    parser.add_argument(
        "--version",
        help="Override package version (defaults to reading from package __init__.py)",
    )
    return parser.parse_args(argv)


def _run_build(args) -> int:
    build_args = ["--output-dir", str(args.output_dir)]
    if args.mpy_cross:
        build_args.extend(["--mpy-cross", str(args.mpy_cross)])
    if args.keep_py:
        build_args.append("--keep-py")
    return build_main(build_args)


def _run_manifest(args) -> int:
    manifest_args = [
        "--staging-dir",
        str(args.staging_dir),
        "--staging-subdir",
        args.staging_subdir,
        "--base-url",
        args.base_url,
        "--manifest-output",
        str(args.manifest_output),
        "--package-name",
        args.package_name,
    ]
    if args.version:
        manifest_args.extend(["--version", args.version])
    if not args.no_index:
        manifest_args.extend([
            "--index-output",
            str(args.index_output),
            "--manifest-url",
            args.manifest_url,
        ])
    return manifest_main(manifest_args)


def main(argv=None) -> int:
    args = _parse_args(argv)

    if not args.skip_stage:
        exit_code = _run_build(args)
        if exit_code:
            return exit_code

    if not args.skip_manifest:
        return _run_manifest(args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
