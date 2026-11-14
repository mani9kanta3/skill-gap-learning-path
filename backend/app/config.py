"""
Settings for the API and the loader, read once from backend/.env.

Kept in one place so a missing value fails with one clear message at
startup, not as a confusing error in the middle of a request.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env")


def get(name, default=None):
    return os.getenv(name, default)


DB_NAME = get("DB_NAME", "skill_gap")
DB_USER = get("DB_USER", "postgres")
DB_PASSWORD = get("DB_PASSWORD", "")
DB_HOST = get("DB_HOST", "localhost")
DB_PORT = get("DB_PORT", "5432")
# Hosted Postgres wants SSL; a laptop does not care.
DB_SSLMODE = get("DB_SSLMODE", "prefer")

# The frontend's address, for CORS. Comma-separated.
CORS_ORIGINS = [o.strip() for o in get("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

OUTPUT_DIR = REPO_ROOT / "output"
