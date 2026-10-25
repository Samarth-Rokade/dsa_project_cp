"""Blood inventory endpoints."""
import re
from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..constants import BAG_STATUSES, BLOOD_GROUPS
from ..database import get_db
from ..domain.sorting import COMPLEXITY_NOTES, sort_bags
from ..domain.state import InMemoryState, get_state
from ..errors import AppError
from ..models import BloodBag
from ..schemas import BagCreate, BagUpdate, BloodGroup
from ..serializers import bag_out, effective_status

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])

SortField = Literal["expiry_date", "collection_date", "blood_group", "bag_id"]
StatusFilter = Literal["available", "reserved", "dispatched", "expired", "discarded"]


@router.get("")
def list_inventory(
    blood_group: Optional[BloodGroup] = None,
    status: Optional[StatusFilter] = None,
    search: Optional[str] = None,
    sort_by: SortField = "expiry_date",
    order: Literal["asc", "desc"] = "asc",
    algorithm: Literal["merge", "quick"] = "merge",
    db: Session = Depends(get_db),
):
    today = date.today()
    all_bags = [bag_out(b, today) for b in db.scalars(select(BloodBag))]

    # filter (a plain linear scan over the snapshot)
    needle = search.strip().lower() if search else ""
    rows = []
    for bag in all_bags:
        if blood_group and bag["blood_group"] != blood_group:
            continue
        if status and bag["effective_status"] != status:
            continue
        if needle and needle not in bag["bag_id"].lower():
            continue
        rows.append(bag)

    # sort with OUR merge sort / quick sort
    result = sort_bags(rows, sort_by, order, algorithm)
    return {
        "items": result.items,
        "count": len(result.items),
        "total": len(all_bags),
        "sort": {
            "algorithm": algorithm,
            "sort_by": sort_by,
            "order": order,
            "comparisons": result.comparisons,
            "data_moves": result.data_moves,
            **COMPLEXITY_NOTES[algorithm],
        },
    }


@router.get("/summary")
def inventory_summary(db: Session = Depends(get_db)):
    today = date.today()
    by_group = {g: {s: 0 for s in BAG_STATUSES} for g in BLOOD_GROUPS}
    for bag in db.scalars(select(BloodBag)):
        by_group[bag.blood_group][effective_status(bag, today)] += 1
    for counts in by_group.values():
        counts["total"] = sum(counts[s] for s in BAG_STATUSES)
    totals = {s: sum(c[s] for c in by_group.values()) for s in BAG_STATUSES}
    totals["total"] = sum(totals[s] for s in BAG_STATUSES)
    return {"by_group": by_group, "totals": totals}


@router.post("/sweep-expired")
def sweep_expired(db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    """Move every expired bag out of the FEFO heaps and mark it 'expired' in the database."""
    with state.lock:
        removed = state.fefo.purge_expired(date.today())
        ids = [b.bag_id for b in removed]
        if ids:
            db.execute(
                update(BloodBag)
                .where(BloodBag.bag_id.in_(ids), BloodBag.status == "available")
                .values(status="expired", updated_at=datetime.now())
            )
            db.commit()
    return {"expired_bag_ids": ids, "count": len(ids)}


@router.get("/{bag_id}")
def get_bag(bag_id: str, db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    bag = _find_bag(bag_id, db, state)
    return bag_out(bag, date.today())


@router.post("", status_code=201)
def add_bag(body: BagCreate, db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    with state.lock:
        bag_id = body.bag_id or _next_bag_id(state)
        if state.bag_index.contains(bag_id):               # hash-table lookup, O(1) average
            raise AppError(409, f"Bag ID {bag_id} already exists", {"bag_id": "This bag ID is already used"})
        bag = BloodBag(
            bag_id=bag_id,
            blood_group=body.blood_group,
            collection_date=body.collection_date,
            expiry_date=body.expiry_date,
            volume_ml=body.volume_ml,
            location=body.location,
            status="available",
        )
        db.add(bag)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise AppError(409, f"Bag ID {bag_id} already exists", {"bag_id": "This bag ID is already used"})
        state.add_bag(bag)                                  # heap insert, O(log n)
    return bag_out(bag, date.today())


@router.patch("/{bag_id}")
def update_bag(bag_id: str, body: BagUpdate, db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    with state.lock:
        bag = _find_bag(bag_id, db, state)
        today = date.today()
        current = effective_status(bag, today)

        if current in ("dispatched", "discarded"):
            raise AppError(409, f"A {current} bag can no longer be changed")
        changes = body.model_dump(exclude_unset=True)
        if current == "expired" and set(changes) - {"status"}:
            raise AppError(409, "An expired bag can only be discarded")
        if current == "expired" and changes.get("status") not in (None, "discarded"):
            raise AppError(409, "An expired bag can only be discarded")

        collection = changes.get("collection_date", bag.collection_date)
        expiry = changes.get("expiry_date", bag.expiry_date)
        if expiry <= collection:
            raise AppError(422, "Validation failed", {"expiry_date": "Expiry date must be later than the collection date"})

        for field, value in changes.items():
            if value is not None:
                setattr(bag, field, value)
        db.commit()
        state.rebuild(db)                                   # heaps re-synchronised with the database
    return bag_out(bag, date.today())


# ---------- helpers ----------
def _find_bag(bag_id, db, state):
    pk = state.bag_index.get(bag_id.strip().upper())        # hash-table index -> primary key
    bag = db.get(BloodBag, pk) if pk is not None else None
    if bag is None:
        raise AppError(404, f"Bag {bag_id} not found")
    return bag


def _next_bag_id(state):
    highest = 1000
    for key in state.bag_index.keys():
        m = re.fullmatch(r"BAG-(\d+)", key)
        if m:
            highest = max(highest, int(m.group(1)))
    return f"BAG-{highest + 1}"
