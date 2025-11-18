#!/usr/bin/env python3
"""Build a mip-compatible package layout for mqtt-pico-swarm.

Copies MicroPython-friendly modules from ``src/mqtt_pico_swarm`` into
``build/mip/lib`` so they can be referenced from a mip manifest. Optionally
runs ``mpy-cross`` to compile staged ``.py`` files to ``.mpy`` bytecode.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

PACKAGE_SRC = Path("src/mqtt_pico_swarm")
OUTPUT_DEFAULT = Path("build/mip")
LIB_SUBDIR = "lib"


def _copy_package(src: Path, dest: Path) -> None:
    if not src.is_dir():
        raise FileNotFoundError(f"Package source directory is missing: {src}")

    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "*.bak"),
    )


def _iter_py_files(path: Path) -> Iterable[Path]:
    return path.rglob("*.py")


def _compile_to_mpy(py_files: Iterable[Path], mpy_cross: Path, keep_py: bool) -> None:
    for py_file in py_files:
        output_file = py_file.with_suffix(".mpy")
        cmd = [str(mpy_cross), str(py_file), "-o", str(output_file)]
        subprocess.run(cmd, check=True)
        if not keep_py:
            py_file.unlink()


def _parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build mip package layout")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DEFAULT,
        help="Destination directory for mip package (default: build/mip)",
    )
    parser.add_argument(
        "--mpy-cross",
        type=Path,
        help="Optional path to mpy-cross binary for compiling staged .py files",
    )
    parser.add_argument(
        "--keep-py",
        action="store_true",
        help="Keep original .py files alongside generated .mpy files",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _parse_args(argv)

    project_root = Path(__file__).resolve().parent.parent
    src_dir = project_root / PACKAGE_SRC
    output_dir = project_root / args.output_dir
    lib_dir = output_dir / LIB_SUBDIR
    target_pkg_dir = lib_dir / PACKAGE_SRC.name

    print(f"Staging package from {src_dir} to {target_pkg_dir}")
    _copy_package(src_dir, target_pkg_dir)

    if args.mpy_cross:
        mpy_cross_path = args.mpy_cross.expanduser()
        if not mpy_cross_path.exists():
            raise FileNotFoundError(f"mpy-cross not found at {mpy_cross_path}")
        print(f"Compiling staged files with mpy-cross: {mpy_cross_path}")
        _compile_to_mpy(_iter_py_files(target_pkg_dir), mpy_cross_path, args.keep_py)

    print(f"Mip package staged at {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))