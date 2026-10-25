# filepath: config/settings_pythonanywhere.py
import os
from pathlib import Path

from deploy.pythonanywhere import load_configuration

_host_config = load_configuration()
os.environ.update(
    DJANGO_SECRET_KEY=_host_config["secret_key"],
    DJANGO_ALLOWED_HOSTS=_host_config["hostname"],
    DJANGO_DEBUG="false",
    DJANGO_DATA_DIR=str(Path(__file__).resolve().parent.parent / "var" / "pythonanywhere"),
)

from .settings import *  # noqa: E402,F403

STATIC_URL = "/static/"
STATIC_ROOT = DATA_DIR / "static"  # noqa: F405
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
