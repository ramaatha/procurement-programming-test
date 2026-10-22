# filepath: config/settings.py
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY wajib diisi dengan secret acak minimal 50 karakter.")

debug_value = os.environ.get("DJANGO_DEBUG", "false").strip().lower()
if debug_value not in {"true", "false"}:
    raise ImproperlyConfigured("DJANGO_DEBUG harus true atau false.")
DEBUG = debug_value == "true"
hosts_value = os.environ.get("DJANGO_ALLOWED_HOSTS", "").strip()
ALLOWED_HOSTS = [host.strip() for host in hosts_value.split(",") if host.strip()]
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS wajib diisi saat DEBUG=false.")
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]"]
if any("*" in host or "://" in host or "/" in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS harus berisi hostname eksplisit tanpa wildcard.")
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts.apps.AccountsConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
DATA_DIR = Path(os.environ.get("DJANGO_DATA_DIR", str(BASE_DIR / "var"))).resolve()
if not DATA_DIR.is_relative_to(BASE_DIR):
    raise ImproperlyConfigured("DJANGO_DATA_DIR harus berada di dalam folder proyek.")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": DATA_DIR / "db.sqlite3",
    "OPTIONS": {"transaction_mode": "IMMEDIATE", "timeout": 5},
    "TEST": {"NAME": DATA_DIR / "test.sqlite3"},
    "ATOMIC_REQUESTS": False,
}}
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "var" / "static"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
