"""Settings and demo-data reset."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..constants import DISCLAIMER
from ..database import get_db
from ..domain.settings import get_settings, save_settings
from ..domain.state import InMemoryState, get_state
from ..schemas import SettingsUpdate
from ..seed import reset_demo_data

router = APIRouter(prefix="/api", tags=["Settings"])


@router.get("/settings")
def read_settings(db: Session = Depends(get_db)):
    return {**get_settings(db), "disclaimer": DISCLAIMER}


@router.put("/settings")
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    with state.lock:
        updated = save_settings(db, body.expiring_soon_days, body.compatibility_mode)
    return {**updated, "disclaimer": DISCLAIMER}


@router.post("/admin/reset-demo")
def reset_demo(db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    """Delete ALL data and load the synthetic demo data again (the UI asks for confirmation first)."""
    with state.lock:
        counts = reset_demo_data(db)
        state.rebuild(db)
    return {"message": "Demo data reset", **counts}
