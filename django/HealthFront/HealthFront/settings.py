"""
Django settings for HealthFront.

SQLite by default (`db.sqlite3`). Set DJANGO_USE_POSTGRES=1 plus Postgres vars in `.env`
to use Postgres (same pattern as companion/ai/db_query). Notes: django/HealthFront/MIGRATE_DB.txt
"""

from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = BASE_DIR.parent.parent
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(BASE_DIR / ".env", override=True)


SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-^&n-9yeez+g(gq6*v062+#ha%o+8a0nb+-a)p-$kow3#eqhgl%",
)
DEBUG = os.getenv("DEBUG", "True").strip().lower() in ("1", "true", "yes")
_ALLOWED = os.getenv("DJANGO_ALLOWED_HOSTS", "").strip()
ALLOWED_HOSTS = [h.strip() for h in _ALLOWED.split(",") if h.strip()]


def _postgres_database():
    from pg_env import postgres_params_from_env

    p = postgres_params_from_env()
    user, password, host, port, name, sslmode = (
        p["user"],
        p["password"],
        p["host"],
        p["port"],
        p["dbname"],
        p["sslmode"],
    )
    if not all([user, password, host, port, name]):
        raise ImproperlyConfigured(
            "DJANGO_USE_POSTGRES=1 but Postgres env incomplete. "
            "Set user, password, host, port, dbname in .env (see MIGRATE_DB.txt)."
        )
    hl = (host or "").lower()
    ps = str(port).strip()
    pooling = "pooler" in hl or ps == "6543"
    cfg = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": user,
        "PASSWORD": password,
        "HOST": host,
        "PORT": port,
        "OPTIONS": {"sslmode": sslmode or "require"},
        "CONN_MAX_AGE": int(os.getenv("CONN_MAX_AGE", "0" if pooling else "600")),
    }
    if pooling:
        cfg["DISABLE_SERVER_SIDE_CURSORS"] = True
    return cfg


def _sqlite_database():
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }


_use_pg = os.getenv("DJANGO_USE_POSTGRES", "").strip().lower() in ("1", "true", "yes")
DATABASES = {
    "default": _postgres_database() if _use_pg else _sqlite_database(),
}


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "companion",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "HealthFront.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "HealthFront.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
