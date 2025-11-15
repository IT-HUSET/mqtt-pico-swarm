#!/usr/bin/env python3
"""Upload the internal temperature sensor demo to a connected Pico W using mpremote."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SRC = REPO_ROOT / "src" / "mqtt_pico_swarm"
DEMO_MAIN = REPO_ROOT / "examples" / "internal-temp-sensor" / "main.py"
DEMO_CONFIG = REPO_ROOT / "examples" / "internal-temp-sensor" / "config.json"
UMQTT_PACKAGE = "micropython-umqtt.simple2"


def _ensure_paths_exist() -> None:
    required = [PACKAGE_SRC, DEMO_MAIN]
    missing = [path for path in required if not path.exists()]
    if missing:
        print("Följande filer/kataloger saknas:")
        for path in missing:
            print(f"  - {path}")
        raise SystemExit(
            "Kör skriptet från repo-roten och säkerställ att källfilerna finns."
        )


def _run_mpremote(port: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["mpremote", "connect", port, *args]
    print("$", " ".join(cmd))
    try:
        return subprocess.run(cmd, check=check)
    except FileNotFoundError as exc:
        raise SystemExit(
            "mpremote hittades inte. Installera med 'python3 -m pip install mpremote'."
        ) from exc
    except subprocess.CalledProcessError as exc:
        if check:
            print(
                "Tips: Kontrollera att inga andra program (t.ex. MicroPico REPL) använder "
                "Picon och ange rätt --port."
            )
            raise SystemExit(f"mpremote-kommando misslyckades (kod {exc.returncode}).") from exc
        return exc


def _download_and_extract(package_name: str, tmpdir: Path) -> Path:
    api_url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with urllib.request.urlopen(api_url) as response:
            metadata = json.load(response)
    except Exception as error:
        raise SystemExit(
            f"Misslyckades att hämta metadata för {package_name}: {error}"
        ) from error

    urls = metadata.get("urls", [])
    sdist = next((item for item in urls if item.get("packagetype") == "sdist"), None)
    if not sdist:
        raise SystemExit(f"Hittade ingen sdist-release för {package_name}.")

    tar_url = sdist.get("url")
    if not tar_url:
        raise SystemExit(f"Saknar URL för {package_name}.")

    file_name = Path(urllib.parse.urlparse(tar_url).path).name
    download_path = tmpdir / file_name

    try:
        with urllib.request.urlopen(tar_url) as response:
            download_path.write_bytes(response.read())
    except Exception as error:
        raise SystemExit(f"Misslyckades att ladda ned {package_name}: {error}") from error

    if file_name.endswith(".tar.gz"):
        try:
            with tarfile.open(download_path, "r:gz") as archive:
                archive.extractall(path=tmpdir)
        except tarfile.TarError as error:
            raise SystemExit(f"Misslyckades att packa upp {package_name}: {error}") from error
        package_root = download_path.with_suffix("")
        package_root = package_root.with_suffix("")
    elif file_name.endswith(".zip"):
        try:
            with zipfile.ZipFile(download_path) as archive:
                archive.extractall(path=tmpdir)
        except zipfile.BadZipFile as error:
            raise SystemExit(f"Misslyckades att packa upp {package_name}: {error}") from error
        package_root = download_path.with_suffix("")
    else:
        raise SystemExit(f"Okänt arkivformat för {package_name}: {file_name}")

    return Path(tmpdir) / package_root.name


def _install_umqtt(port: str) -> None:
    print("Installerar micropython-umqtt.simple2 på enheten...")
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        package_root = _download_and_extract(UMQTT_PACKAGE, tmpdir)
        umqtt_dir = package_root / "umqtt"

        if not umqtt_dir.exists():
            raise SystemExit(
                "Hittade ingen katalog 'umqtt' i paketet micropython-umqtt.simple2."
            )

        _run_mpremote(port, "fs", "mkdir", "lib", check=False)
        _run_mpremote(port, "fs", "mkdir", "lib/umqtt", check=False)
        _run_mpremote(port, "cp", "-r", str(umqtt_dir), ":/lib/")
        print("umqtt.simple2 installerad.")


def main(argv: list[str] | None = None) -> int:
    print("börjar...")
    parser = argparse.ArgumentParser(description="Deploy basic Pico demo via mpremote")
    parser.add_argument(
        "--port",
        default="auto",
        help="Serieport (auto, /dev/ttyACM0, /dev/tty.usbmodem1101, etc.)",
    )
    parser.add_argument(
        "--skip-config",
        action="store_true",
        help="Hoppa över att kopiera config.json",
    )
    parser.add_argument(
        "--install-umqtt",
        action="store_true",
        help="Hämta och installera micropython-umqtt.simple2 på Pico W",
    )
    args = parser.parse_args(argv)

    _ensure_paths_exist()

    # Se till att lib-katalogen finns
    _run_mpremote(args.port, "fs", "mkdir", "lib", check=False)

    if args.install_umqtt:
        _install_umqtt(args.port)

    # Kopiera paketet till /lib
    _run_mpremote(
        args.port,
        "cp",
        "-r",
        str(PACKAGE_SRC),
        ":/lib/",
    )

    # Kopiera demo-scriptet till rot
    _run_mpremote(
        args.port,
        "cp",
        str(DEMO_MAIN),
        ":main.py",
    )

    if not args.skip_config:
        if DEMO_CONFIG.exists():
            _run_mpremote(
                args.port,
                "cp",
                str(DEMO_CONFIG),
                ":config.json",
            )
        else:
            print("Varning: config.json saknas lokalt – hoppar över kopiering.")

    print("\nKlar! Tryck Ctrl+D i REPL och kör 'import main'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())