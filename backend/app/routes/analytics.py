"""Dashboard numbers. Every figure is computed from the database, nothing is hard-coded."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..constants import BLOOD_GROUPS, DISCLAIMER, WAITING_STATUSES
from ..database import get_db
from ..domain.settings import get_settings
from ..domain.sorting import sort_bags
from ..domain.state import InMemoryState, get_state
from ..dsa.merge_sort import merge_sort
from ..models import BloodBag, Dispatch, DispatchItem, HospitalRequest
from ..serializers import bag_out, dispatch_out, request_out

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    today = date.today()
    settings = get_settings(db)
    warn_until = today + timedelta(days=settings["expiring_soon_days"])

    bags = list(db.scalars(select(BloodBag)))
    requests = list(db.scalars(select(HospitalRequest)))

    usable = [b for b in bags if b.status == "available" and b.expiry_date >= today]
    expiring = [b for b in usable if b.expiry_date <= warn_until]
    expired = [b for b in bags if b.status == "expired" or (b.status == "available" and b.expiry_date < today)]
    waiting = [r for r in requests if r.status in WAITING_STATUSES]

    stock_by_group = []
    for group in BLOOD_GROUPS:
        group_usable = [b for b in usable if b.blood_group == group]
        stock_by_group.append({
            "blood_group": group,
            "available": len(group_usable),
            "expiring_soon": len([b for b in group_usable if b.expiry_date <= warn_until]),
            "expired": len([b for b in expired if b.blood_group == group]),
        })

    # most urgent expiries first - sorted with our own merge sort
    expiring_sorted = sort_bags([bag_out(b, today) for b in expiring], "expiry_date", "asc", "merge").items

    # live priority queue straight from the heap
    mode = settings["compatibility_mode"]
    queue = []
    for position, entry in enumerate(state.request_heap.sorted_view()[:6], start=1):
        req = next((r for r in waiting if r.request_id == entry.request_id), None)
        if req is not None:
            queue.append(request_out(req, mode, position))

    recent = db.scalars(
        select(Dispatch)
        .options(selectinload(Dispatch.request), selectinload(Dispatch.items).selectinload(DispatchItem.bag))
    )
    recent_sorted = merge_sort(
        [dispatch_out(d) for d in recent], key=lambda d: (d["processed_at"], d["id"]), reverse=True
    ).items[:5]

    return {
        "today": today.isoformat(),
        "settings": settings,
        "kpis": {
            "available_units": len(usable),
            "registered_bags": len(bags),
            "pending_requests": len(waiting),
            "critical_waiting": len([r for r in waiting if r.urgency_level == 1]),
            "expiring_soon": len(expiring),
            "expired_units": len(expired),
            "dispatched_units": len([b for b in bags if b.status == "dispatched"]),
        },
        "stock_by_group": stock_by_group,
        "expiring_bags": expiring_sorted[:6],
        "priority_queue": queue,
        "recent_dispatches": recent_sorted,
        "disclaimer": DISCLAIMER,
    }
