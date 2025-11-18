#!/usr/bin/env python3
"""Generate mip manifest (and optional index) from staged package files.

This expects ``build_mip_package.py`` to have staged the library under
``build/mip/lib/`` (or a custom staging directory). The script emits a
``package.json``-style document describing file checksums and an optional
index that points to the manifest URL.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable, Optional

PACKAGE_INIT = Path("src/mqtt_pico_swarm/__init__.py")
DEFAULT_STAGING_DIR = Path("build/mip")
DEFAULT_SUBDIR = "lib"
DEFAULT_PACKAGE_NAME = "mqtt-pico-swarm"


def _read_version(init_file: Path) -> Optional[str]:
    if not init_file.exists():
        return None
    for line in init_file.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("__version__"):
            parts = stripped.split("=", 1)
            if len(parts) == 2:
                return parts[1].strip().strip('"\'')
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_files(base_dir: Path) -> Iterable[Path]:
    for path in sorted(base_dir.rglob("*")):
        if path.is_file():
            yield path


def _normalise(path: Path) -> str:
    return str(path).replace("\\", "/")


def build_manifest(staging_dir: Path, base_url: str, version: str, package_name: str) -> dict:
    base_url = base_url.rstrip("/")
    files = []
    for file_path in _iter_files(staging_dir):
        relative = file_path.relative_to(staging_dir)
        relative_str = _normalise(relative)
        files.append(
            {
                "path": relative_str,
                "url": f"{base_url}/{relative_str}",
                "sha256": _sha256(file_path),
                "size": file_path.stat().st_size,
            }
        )

    return {
        "name": package_name,
        "version": version,
        "deps": [],
        "files": files,
    }


def build_index(package_name: str, version: str, manifest_url: str) -> dict:
    return {
        "packages": {
            package_name: {
                "version": version,
                "manifest": manifest_url,
            }
        }
    }


def _parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate mip manifest")
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=DEFAULT_STAGING_DIR,
        help="Directory containing staged files (default: build/mip)",
    )
    parser.add_argument(
        "--staging-subdir",
        default=DEFAULT_SUBDIR,
        help="Subdirectory inside staging to include (default: lib)",
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL where staged files will be hosted",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        required=True,
        help="Destination JSON file for the manifest",
    )
    parser.add_argument(
        "--index-output",
        type=Path,
        help="Optional JSON file for mip index",
    )
    parser.add_argument(
        "--manifest-url",
        help="Public URL to the manifest (required if --index-output is set)",
    )
    parser.add_argument(
        "--package-name",
        default=DEFAULT_PACKAGE_NAME,
        help=f"Package name (default: {DEFAULT_PACKAGE_NAME})",
    )
    parser.add_argument(
        "--version",
        help="Package version (default: read from src/mqtt_pico_swarm/__init__.py)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _parse_args(argv)

    staging_dir = args.staging_dir / args.staging_subdir
    if not staging_dir.exists():
        raise FileNotFoundError(f"Staging subdir not found: {staging_dir}")

    version = args.version or _read_version(PACKAGE_INIT)
    if not version:
        raise RuntimeError("Unable to determine package version; specify --version explicitly")

    manifest = build_manifest(staging_dir, args.base_url, version, args.package_name)
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote manifest with {len(manifest['files'])} files -> {args.manifest_output}")

    if args.index_output:
        if not args.manifest_url:
            raise ValueError("--manifest-url is required when --index-output is set")
        index = build_index(args.package_name, version, args.manifest_url)
        args.index_output.parent.mkdir(parents=True, exist_ok=True)
        args.index_output.write_text(json.dumps(index, indent=2) + "\n")
        print(f"Wrote index -> {args.index_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
