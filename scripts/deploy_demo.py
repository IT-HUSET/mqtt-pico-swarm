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
DEMOS = {
    "internal-temp-sensor": REPO_ROOT / "examples" / "internal-temp-sensor",
    "seesaw-moist-sensor": REPO_ROOT / "examples" / "seesaw-moist-sensor",
    "external-temp-sensor": REPO_ROOT / "examples" / "external-temp-sensor",
}
UMQTT_PACKAGE = "micropython-umqtt.simple2"
DS18X20_URL = (
    "https://raw.githubusercontent.com/micropython/micropython/"
    "master/drivers/onewire/ds18x20.py"
)


def _ensure_paths_exist(project_root: Path) -> None:
    required = [PACKAGE_SRC, project_root / "main.py"]
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


def _install_ds18x20(port: str) -> None:
    print("Installerar ds18x20 på enheten...")
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        module_path = Path(tmpdir) / "ds18x20.py"

        try:
            with urllib.request.urlopen(DS18X20_URL) as response:  # type: ignore[attr-defined]
                module_path.write_bytes(response.read())
        except Exception as error:  # pragma: no cover - nätverksfel bara vid runtime
            raise SystemExit(f"Misslyckades att ladda ned ds18x20.py: {error}") from error

        _run_mpremote(port, "fs", "mkdir", "lib", check=False)
        _run_mpremote(port, "cp", str(module_path), ":/lib/ds18x20.py")

    print("ds18x20 installerad.")


def _prompt_project_name(default: str) -> str:
    print("Tillgängliga demos:")
    for idx, name in enumerate(sorted(DEMOS.keys()), start=1):
        print(f"  {idx}. {name}")
    response = input(f"Vilken demo vill du deploya? [{default}] ")
    response = response.strip()
    if not response:
        return default
    if response in DEMOS:
        return response
    try:
        idx = int(response)
    except ValueError as error:  # pragma: no cover - endast interaktivt
        raise SystemExit(f"Okänt demoval: {response}") from error
    options = sorted(DEMOS.keys())
    if 1 <= idx <= len(options):
        return options[idx - 1]
    raise SystemExit(f"Demoval #{idx} finns inte. Välj mellan 1 och {len(options)}.")


def _resolve_project(project_arg: str | None) -> tuple[str, Path]:
    default = "internal-temp-sensor"
    if project_arg:
        name = project_arg
    else:
        name = _prompt_project_name(default)

    if name not in DEMOS:
        raise SystemExit(
            "Okänt projektnamn. Tillgängliga värden: " + ", ".join(sorted(DEMOS.keys()))
        )
    return name, DEMOS[name]


def main(argv: list[str] | None = None) -> int:
    print("börjar...")
    parser = argparse.ArgumentParser(description="Deploy Pico demo via mpremote")
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
    parser.add_argument(
        "--project",
        default=None,
        help=(
            "Sätt vilket demo-projekt som ska deployas utan prompt "
            "(internal-temp-sensor, seesaw-moist-sensor, external-temp-sensor)"
        ),
    )
    args = parser.parse_args(argv)

    project_name, project_root = _resolve_project(args.project)
    demo_main = project_root / "main.py"
    demo_config = project_root / "config.json"

    _ensure_paths_exist(project_root)

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
        str(demo_main),
        ":main.py",
    )

    # Kopiera eventuella extra .py-filer från demo-katalogen (t.ex. DS18B20.py)
    for module in project_root.glob("*.py"):
        if module.name == "main.py":
            continue
        _run_mpremote(
            args.port,
            "cp",
            str(module),
            f":/{module.name}",
        )

    if not args.skip_config:
        if demo_config.exists():
            _run_mpremote(
                args.port,
                "cp",
                str(demo_config),
                ":config.json",
            )
        else:
            print("Varning: config.json saknas lokalt – hoppar över kopiering.")

    print(
        f"\nKlar! Deployade '{project_name}'. Tryck Ctrl+D i REPL och kör 'import main'."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())