"""Postgres credentials from .env shared by Django and ai/db_query."""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

_BASE = Path(__file__).resolve().parent
_REPO_ROOT = _BASE.parent.parent
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_BASE / ".env", override=True)

_POOLER = re.compile(r"pooler\.supabase\.com", re.IGNORECASE)


def _maybe_pool_port_6543(params: dict) -> dict:
    """Supabase transaction pool usually needs port 6543 on *.pooler* host (not 5432)."""
    if os.getenv("SUPABASE_DISABLE_POOLER_FIX", "").strip().lower() in ("1", "true", "yes"):
        return params
    host = (params.get("host") or "").strip()
    port = str(params.get("port") or "").strip()
    if not host or not _POOLER.search(host):
        return params
    if port in ("5432", ""):
        return {**params, "port": "6543"}
    return params


def postgres_params_from_env() -> dict[str, str | None]:
    def _s(v):
        return v.strip() if isinstance(v, str) else v

    dj_u = (os.getenv("DJANGO_DB_USER") or "").strip()
    raw_user = (os.getenv("user") or "").strip()
    user = _s(dj_u or raw_user or "")

    password = os.getenv("DJANGO_DB_PASSWORD") or os.getenv("password")
    if isinstance(password, str):
        password = password.strip()

    host = _s(os.getenv("DJANGO_DB_HOST") or os.getenv("host") or "")
    port_raw = os.getenv("DJANGO_DB_PORT") or os.getenv("port") or "5432"
    port = str(port_raw).strip()
    dbname = _s(os.getenv("DJANGO_DB_NAME") or os.getenv("dbname") or "")
    sslmode = os.getenv("PGSSLMODE", "require")

    return _maybe_pool_port_6543(
        {
            "user": user or None,
            "password": password,
            "host": host or None,
            "port": port,
            "dbname": dbname or None,
            "sslmode": sslmode,
        }
    )
