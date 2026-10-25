"""
Configuration.

The database is chosen with ONE setting, DATABASE_URL. SQLAlchemy hides the differences
between databases, so moving from SQLite (development) to PostgreSQL/MySQL later only needs:

    set DATABASE_URL=postgresql+psycopg://user:password@localhost/bloodbank
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'bloodbank.db').as_posix()}")

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
