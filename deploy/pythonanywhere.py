# filepath: deploy/pythonanywhere.py
"""Create and read the private configuration shared by console and WSGI."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets

from django.core.exceptions import ImproperlyConfigured


DEFAULT_CONFIG = Path.home() / ".config" / "procurement-demo" / "environment.json"
HOST_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.(?:eu\.)?pythonanywhere\.com")


def validate_hostname(value: object) -> str:
    if not isinstance(value, str) or not HOST_PATTERN.fullmatch(value):
        raise ValueError("Hostname PythonAnywhere tidak valid.")
    return value


def load_configuration() -> dict[str, str]:
    path = Path(os.environ.get("PROCUREMENT_HOST_CONFIG", str(DEFAULT_CONFIG)))
    try:
        if path.stat().st_size > 16_384:
            raise ValueError
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"hostname", "secret_key"}:
            raise ValueError
        validate_hostname(data["hostname"])
        secret = data["secret_key"]
        if not isinstance(secret, str) or not 50 <= len(secret) <= 4096 or secret.startswith("django-insecure-"):
            raise ValueError
    except (OSError, UnicodeError, ValueError):
        raise ImproperlyConfigured(
            "Konfigurasi hosting tidak tersedia atau tidak valid. "
            "Jalankan python -m deploy.pythonanywhere configure terlebih dahulu."
        ) from None
    return data


def create_configuration(hostname: str, path: Path) -> None:
    hostname = validate_hostname(hostname)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError("Konfigurasi hosting sudah ada; secret tidak ditimpa.") from None
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump({"hostname": hostname, "secret_key": secrets.token_urlsafe(64)}, handle)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Siapkan konfigurasi privat demo PythonAnywhere.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    configure = subcommands.add_parser("configure")
    configure.add_argument("--hostname", required=True)
    configure.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    try:
        create_configuration(args.hostname, args.config)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Konfigurasi privat tersimpan di {args.config}. Secret tidak ditampilkan.")


if __name__ == "__main__":
    main()
