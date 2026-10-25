"""Hospital request endpoints (including Process Next)."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import WAITING_STATUSES
from ..database import get_db
from ..domain.allocation_service import NoWaitingRequests, process_next_request
from ..domain.settings import get_settings
from ..domain.state import InMemoryState, get_state
from ..dsa.merge_sort import merge_sort
from ..errors import AppError
from ..models import HospitalRequest
from ..schemas import RequestCreate
from ..serializers import request_out

router = APIRouter(prefix="/api/requests", tags=["Requests"])

REQUEST_SORT_KEYS = {
    # waiting requests first (in heap order), finished ones after them
    "priority": lambda r: (r["status"] not in WAITING_STATUSES, r["urgency_level"], r["arrival_sequence"], r["request_id"]),
    "arrival": lambda r: r["arrival_sequence"],
    "units_needed": lambda r: (r["units_needed"], r["arrival_sequence"]),
}


def _queue_positions(state):
    """request_id -> position in the live priority heap (1 = processed next)."""
    return {e.request_id: i + 1 for i, e in enumerate(state.request_heap.sorted_view())}


@router.get("")
def list_requests(
    status: Optional[Literal["pending", "partially_fulfilled", "fulfilled", "cancelled"]] = None,
    urgency: Optional[Literal[1, 2, 3]] = None,
    search: Optional[str] = None,
    sort_by: Literal["priority", "arrival", "units_needed"] = "priority",
    order: Literal["asc", "desc"] = "asc",
    db: Session = Depends(get_db),
    state: InMemoryState = Depends(get_state),
):
    mode = get_settings(db)["compatibility_mode"]
    positions = _queue_positions(state)
    needle = search.strip().lower() if search else ""

    rows = []
    for req in db.scalars(select(HospitalRequest)):
        if status and req.status != status:
            continue
        if urgency and req.urgency_level != urgency:
            continue
        if needle and needle not in req.request_id.lower() and needle not in req.hospital_name.lower():
            continue
        rows.append(request_out(req, mode, positions.get(req.request_id) if req.status in WAITING_STATUSES else None))

    result = merge_sort(rows, key=REQUEST_SORT_KEYS[sort_by], reverse=(order == "desc"))
    return {"items": result.items, "count": len(result.items)}


@router.get("/queue")
def priority_queue(db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    """Waiting requests in the exact order the heap will hand them out."""
    mode = get_settings(db)["compatibility_mode"]
    items = []
    for position, entry in enumerate(state.request_heap.sorted_view(), start=1):
        req = db.scalar(select(HospitalRequest).where(HospitalRequest.request_id == entry.request_id))
        if req is not None and req.status in WAITING_STATUSES:
            items.append(request_out(req, mode, position))
    return {"items": items, "count": len(items)}


@router.get("/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    pk = state.request_index.get(request_id.strip().upper())
    req = db.get(HospitalRequest, pk) if pk is not None else None
    if req is None:
        raise AppError(404, f"Request {request_id} not found")
    mode = get_settings(db)["compatibility_mode"]
    position = _queue_positions(state).get(req.request_id) if req.status in WAITING_STATUSES else None
    return request_out(req, mode, position)


@router.post("", status_code=201)
def create_request(body: RequestCreate, db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    with state.lock:
        sequence = (db.scalar(select(func.max(HospitalRequest.arrival_sequence))) or 0) + 1
        req = HospitalRequest(
            request_id=f"REQ-{sequence:04d}",
            hospital_name=body.hospital_name,
            required_blood_group=body.required_blood_group,
            units_needed=body.units_needed,
            units_allocated=0,
            urgency_level=body.urgency_level,
            arrival_sequence=sequence,
            status="pending",
            notes=(body.notes or "").strip() or None,
        )
        db.add(req)
        db.commit()
        state.add_request(req)                              # heap insert, O(log n)
        mode = get_settings(db)["compatibility_mode"]
        position = _queue_positions(state).get(req.request_id)
    return request_out(req, mode, position)


@router.patch("/{request_id}/cancel")
def cancel_request(request_id: str, db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    with state.lock:
        pk = state.request_index.get(request_id.strip().upper())
        req = db.get(HospitalRequest, pk) if pk is not None else None
        if req is None:
            raise AppError(404, f"Request {request_id} not found")
        if req.status not in WAITING_STATUSES:
            raise AppError(409, f"A {req.status.replace('_', ' ')} request cannot be cancelled")
        req.status = "cancelled"
        db.commit()
        state.rebuild(db)                                   # heap rebuilt from the database: O(n) heapify
    return request_out(req, get_settings(db)["compatibility_mode"])


@router.post("/process-next")
def process_next(db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    try:
        return process_next_request(db, state)
    except NoWaitingRequests:
        raise AppError(409, "There are no waiting requests to process")
