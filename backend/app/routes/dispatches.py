"""Dispatch history (read-only: there is deliberately no edit/delete endpoint)."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..dsa.merge_sort import merge_sort
from ..errors import AppError
from ..models import Dispatch, DispatchItem
from ..serializers import dispatch_out

router = APIRouter(prefix="/api/dispatches", tags=["Dispatch history"])


def _query():
    return select(Dispatch).options(
        selectinload(Dispatch.request),
        selectinload(Dispatch.items).selectinload(DispatchItem.bag),
    )


@router.get("")
def list_dispatches(
    order: Literal["asc", "desc"] = "desc",
    result: Optional[Literal["fulfilled", "partially_fulfilled", "no_stock"]] = None,
    db: Session = Depends(get_db),
):
    rows = [dispatch_out(d) for d in db.scalars(_query()) if not result or d.result == result]
    # history sorted by processing time with OUR merge sort (id breaks ties)
    sorted_rows = merge_sort(rows, key=lambda d: (d["processed_at"], d["id"]), reverse=(order == "desc"))
    return {"items": sorted_rows.items, "count": len(sorted_rows.items)}


@router.get("/{dispatch_id}")
def get_dispatch(dispatch_id: int, db: Session = Depends(get_db)):
    d = db.scalar(_query().where(Dispatch.id == dispatch_id))
    if d is None:
        raise AppError(404, f"Dispatch {dispatch_id} not found")
    return dispatch_out(d)
