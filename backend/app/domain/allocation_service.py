"""
Allocation service: "Process Next Request".

All allocation rules live here, independent of HTTP and of the UI.

Flow for ONE click on "Process Next Request"
    1. Remove expired bags from the FEFO heaps and mark them 'expired' in the database.
    2. Extract the highest-priority request from the request heap (urgency, then arrival).
    3. Look up the compatible donor groups for that request (compatibility table).
    4. If none of those groups has stock, the request STAYS PENDING and the next request in
       priority order is tried instead (so a blocked request cannot starve the others).
    5. Allocate bag by bag with FEFO: always the earliest expiry among the compatible groups.
    6. Save everything (bags, request, dispatch log) in ONE database transaction.
    7. Re-insert requests that still need stock into the heap (original arrival sequence kept).
    If anything fails the transaction is rolled back and the in-memory structures are rebuilt
    from the database, so a failure can never be reported as a success.

Requeue policy: a partially fulfilled request goes back into the heap with its remaining
units and its ORIGINAL arrival sequence. Only ONE request is allocated per call.
"""
from datetime import date, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..constants import URGENCY_LABELS, WAITING_STATUSES
from ..models import BloodBag, Dispatch, DispatchItem, HospitalRequest
from .compatibility import get_compatible_donor_groups
from .priority import RequestEntry
from .settings import get_settings
from .state import InMemoryState


class NoWaitingRequests(Exception):
    """There is nothing in the priority queue to process."""


def process_next_request(db: Session, state: InMemoryState, today: date = None):
    today = today or date.today()
    mode = get_settings(db)["compatibility_mode"]
    with state.lock:
        try:
            result = _process(db, state, today, mode)
            db.commit()
            return result
        except NoWaitingRequests:
            db.commit()                    # keep the expiry clean-up from step 1
            raise
        except Exception:
            db.rollback()
            state.rebuild(db)              # in-memory structures may be half-changed
            raise


def _process(db, state, today, mode):
    now = datetime.now()

    # ---- 1. expired stock is never eligible ----
    expired = state.fefo.purge_expired(today)
    expired_ids = [b.bag_id for b in expired]
    if expired_ids:
        db.execute(
            update(BloodBag)
            .where(BloodBag.bag_id.in_(expired_ids), BloodBag.status == "available")
            .values(status="expired", updated_at=now)
        )

    # ---- 2-4. choose the request: highest priority that has some compatible stock ----
    examined = []                          # (heap entry, db row, donor groups) popped in this call
    chosen = None
    while True:
        entry = state.request_heap.extract()
        if entry is None:
            break
        req = db.scalar(select(HospitalRequest).where(HospitalRequest.request_id == entry.request_id))
        if req is None or req.status not in WAITING_STATUSES:
            continue                       # stale heap entry (cancelled / fulfilled): drop it
        groups = get_compatible_donor_groups(req.required_blood_group, mode)
        examined.append((entry, req, groups))
        if state.fefo.count_in(groups) > 0:
            chosen = examined[-1]
            break

    if not examined:
        raise NoWaitingRequests()

    # ---- nothing could be allocated for any waiting request ----
    if chosen is None:
        _, top_req, top_groups = examined[0]
        remaining = top_req.units_needed - top_req.units_allocated
        summary_parts = [
            _priority_sentence(db, top_req, first=True),
            _compat_sentence(top_req, top_groups, mode),
            f"No compatible stock is available. Shortage: {remaining} unit(s) still needed; "
            "the request stays pending.",
        ]
        if len(examined) > 1:
            summary_parts.append(
                "Other waiting requests were checked too and also have no compatible stock: "
                + ", ".join(r.request_id for _, r, _ in examined[1:]) + "."
            )
        if expired_ids:
            summary_parts.append("Expired bags removed first: " + ", ".join(expired_ids) + ".")
        dispatch = _log_dispatch(db, top_req, "no_stock", [], remaining, top_groups, " ".join(summary_parts), now)
        for entry, _, _ in examined:       # everything goes back into the heap
            state.request_heap.insert(entry)
        return _result("no_stock", dispatch, top_req, [], top_groups, mode, summary_parts, [], expired_ids)

    # ---- 5. FEFO allocation for the chosen request ----
    entry, req, groups = chosen
    needed = req.units_needed - req.units_allocated
    picked = []
    while len(picked) < needed:
        bag = state.fefo.pop_earliest_among(groups)
        if bag is None:
            break
        picked.append(bag)

    bag_rows = []
    if picked:
        bag_rows = list(db.scalars(select(BloodBag).where(BloodBag.bag_id.in_([b.bag_id for b in picked]))))
        by_id = {row.bag_id: row for row in bag_rows}
        bag_rows = [by_id[b.bag_id] for b in picked]       # keep FEFO order
        for row in bag_rows:
            if row.status != "available":                  # defensive: a bag is dispatched at most once
                raise RuntimeError(f"Bag {row.bag_id} is not available")
            row.status = "dispatched"

    req.units_allocated += len(picked)
    remaining = req.units_needed - req.units_allocated
    req.status = "fulfilled" if remaining == 0 else "partially_fulfilled"
    outcome = "fulfilled" if remaining == 0 else "partially_fulfilled"

    skipped = examined[:-1]
    summary_parts = [
        _priority_sentence(db, req, first=(len(skipped) == 0), skipped=[r.request_id for _, r, _ in skipped]),
        _compat_sentence(req, groups, mode),
        "Bags chosen by FEFO (earliest expiry first): "
        + ", ".join(f"{b.bag_id} ({b.blood_group}, expires {b.expiry_date.isoformat()})" for b in picked) + ".",
    ]
    if remaining > 0:
        summary_parts.append(
            f"Shortage: only {len(picked)} of {needed} unit(s) could be allocated; "
            f"{remaining} unit(s) still needed and the request stays in the queue."
        )
    else:
        summary_parts.append("Request fully fulfilled.")
    if expired_ids:
        summary_parts.append("Expired bags removed first: " + ", ".join(expired_ids) + ".")

    dispatch = _log_dispatch(db, req, outcome, bag_rows, remaining, groups, " ".join(summary_parts), now)

    # ---- 7. requeue ----
    for skipped_entry, _, _ in skipped:
        state.request_heap.insert(skipped_entry)
    if remaining > 0:
        state.request_heap.insert(
            RequestEntry(req.request_id, req.urgency_level, req.arrival_sequence, remaining)
        )

    return _result(outcome, dispatch, req, bag_rows, groups, mode, summary_parts, skipped, expired_ids)


# ---------- helpers ----------
def _log_dispatch(db, req, result, bag_rows, remaining, groups, summary, now):
    dispatch = Dispatch(
        request_pk=req.id,
        processed_at=now,
        units_allocated=len(bag_rows),
        units_remaining=remaining,
        result=result,
        groups_considered=",".join(groups),
        decision_summary=summary,
    )
    db.add(dispatch)
    db.flush()                             # gives the dispatch its id
    for row in bag_rows:
        db.add(DispatchItem(
            dispatch_id=dispatch.id,
            blood_bag_pk=row.id,
            donor_blood_group=row.blood_group,
            expiry_date_at_dispatch=row.expiry_date,
        ))
    db.flush()
    return dispatch


def _priority_sentence(db, req, first, skipped=None):
    label = URGENCY_LABELS[req.urgency_level]
    others = db.scalar(
        select(HospitalRequest.id)
        .where(
            HospitalRequest.status.in_(WAITING_STATUSES),
            HospitalRequest.urgency_level == req.urgency_level,
            HospitalRequest.id != req.id,
        )
        .limit(1)
    )
    if not first:
        return (
            f"{req.request_id} ({req.hospital_name}) was processed. Higher-priority request(s) "
            f"{', '.join(skipped)} had no compatible stock and stay pending, so the next request "
            f"in heap order was served."
        )
    reason = f"{req.request_id} ({req.hospital_name}) was at the root of the priority heap: urgency {req.urgency_level} ({label})"
    if others is not None:
        reason += f". Other requests share this urgency, so the earliest arrival (#{req.arrival_sequence}) won."
    else:
        reason += " is the most urgent level waiting."
    return reason


def _compat_sentence(req, groups, mode):
    label = "simplified educational table" if mode == "educational" else "exact-match only mode"
    return f"Requested group {req.required_blood_group}; donor groups considered ({label}): {', '.join(groups)}."


def _result(outcome, dispatch, req, bag_rows, groups, mode, summary_parts, skipped, expired_ids):
    from ..serializers import request_out         # local import avoids a circular import

    remaining = req.units_needed - req.units_allocated
    return {
        "result": outcome,
        "dispatch_id": dispatch.id,
        "request": request_out(req, mode),
        "priority_reason": summary_parts[0],
        "groups_considered": groups,
        "compatibility_mode": mode,
        "allocated_bags": [
            {"bag_id": r.bag_id, "blood_group": r.blood_group, "expiry_date": r.expiry_date.isoformat()}
            for r in bag_rows
        ],
        "units_allocated_now": len(bag_rows),
        "units_remaining": remaining,
        "shortage_message": (
            f"Shortage: {remaining} unit(s) of {req.required_blood_group} still needed." if remaining > 0 else None
        ),
        "skipped_requests": [
            {"request_id": r.request_id, "hospital_name": r.hospital_name, "reason": "No compatible stock"}
            for _, r, _ in skipped
        ],
        "expired_removed": expired_ids,
        "summary": " ".join(summary_parts),
    }
