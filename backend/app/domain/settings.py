"""Tiny key/value settings stored in the database."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import COMPATIBILITY_MODES, DEFAULT_SETTINGS
from ..models import AppSetting


def get_settings(db: Session):
    rows = {s.key: s.value for s in db.scalars(select(AppSetting))}
    merged = {**DEFAULT_SETTINGS, **rows}
    mode = merged["compatibility_mode"]
    return {
        "expiring_soon_days": int(merged["expiring_soon_days"]),
        "compatibility_mode": mode if mode in COMPATIBILITY_MODES else "educational",
    }


def save_settings(db: Session, expiring_soon_days=None, compatibility_mode=None):
    updates = {}
    if expiring_soon_days is not None:
        updates["expiring_soon_days"] = str(expiring_soon_days)
    if compatibility_mode is not None:
        updates["compatibility_mode"] = compatibility_mode
    for key, value in updates.items():
        row = db.get(AppSetting, key)
        if row is None:
            db.add(AppSetting(key=key, value=value))
        else:
            row.value = value
    db.commit()
    return get_settings(db)
