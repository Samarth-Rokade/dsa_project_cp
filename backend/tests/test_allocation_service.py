import pytest
from sqlalchemy import select

from app.domain.allocation_service import NoWaitingRequests, process_next_request
from app.domain.priority import RequestEntry
from app.domain.settings import save_settings
from app.models import BloodBag, Dispatch, HospitalRequest
from tests.conftest import add_bag, add_request


def bag_status(db, bag_id):
    return db.scalar(select(BloodBag).where(BloodBag.bag_id == bag_id)).status


def test_request_with_enough_stock_is_fulfilled(db, state):
    add_bag(db, state, "B1", "A+", 5)
    add_bag(db, state, "B2", "A+", 9)
    req = add_request(db, state, "A+", 2, 2)
    result = process_next_request(db, state)
    assert result["result"] == "fulfilled"
    assert [b["bag_id"] for b in result["allocated_bags"]] == ["B1", "B2"]
    assert db.get(HospitalRequest, req.id).status == "fulfilled"
    assert bag_status(db, "B1") == bag_status(db, "B2") == "dispatched"
    assert db.query(Dispatch).count() == 1


def test_fefo_order_and_cross_group_alternative(db, state):
    add_bag(db, state, "A-LATE", "A+", 20)
    add_bag(db, state, "O-SOON", "O+", 2)         # compatible alternative that expires first
    add_request(db, state, "A+", 1, 1)
    result = process_next_request(db, state)
    assert [b["bag_id"] for b in result["allocated_bags"]] == ["O-SOON"]
    assert "O+" in result["groups_considered"]


def test_incompatible_stock_is_never_allocated(db, state):
    add_bag(db, state, "B-ONLY", "B+", 3)
    add_request(db, state, "A+", 1, 1)
    result = process_next_request(db, state)
    assert result["result"] == "no_stock"
    assert bag_status(db, "B-ONLY") == "available"


def test_exact_mode_disables_alternatives(db, state):
    save_settings(db, compatibility_mode="exact")
    add_bag(db, state, "O-1", "O+", 2)
    add_request(db, state, "A+", 1, 1)
    assert process_next_request(db, state)["result"] == "no_stock"
    assert bag_status(db, "O-1") == "available"


def test_expired_bags_are_never_allocated_and_get_marked(db, state):
    add_bag(db, state, "OLD", "A+", -2)           # status still 'available' but past expiry
    add_bag(db, state, "FRESH", "A+", 6)
    add_request(db, state, "A+", 2, 1)
    result = process_next_request(db, state)
    assert [b["bag_id"] for b in result["allocated_bags"]] == ["FRESH"]
    assert result["result"] == "partially_fulfilled"
    assert result["expired_removed"] == ["OLD"]
    assert bag_status(db, "OLD") == "expired"


def test_unavailable_bags_are_not_allocated(db, state):
    add_bag(db, state, "GONE", "A+", 5, status="dispatched")
    add_bag(db, state, "HELD", "A+", 5, status="reserved")
    add_bag(db, state, "BIN", "A+", 5, status="discarded")
    add_request(db, state, "A+", 1, 1)
    assert process_next_request(db, state)["result"] == "no_stock"


def test_partial_stock_records_allocated_units_and_shortage(db, state):
    add_bag(db, state, "B1", "B+", 4)
    req = add_request(db, state, "B+", 3, 2)
    result = process_next_request(db, state)
    assert result["result"] == "partially_fulfilled"
    assert result["units_allocated_now"] == 1 and result["units_remaining"] == 2
    assert "Shortage" in result["shortage_message"]
    row = db.get(HospitalRequest, req.id)
    assert row.status == "partially_fulfilled" and row.units_allocated == 1


def test_partial_request_is_requeued_with_original_arrival_sequence(db, state):
    add_bag(db, state, "B1", "B+", 4)
    req = add_request(db, state, "B+", 3, 2)
    process_next_request(db, state)
    root = state.request_heap.peek()
    assert root.request_id == req.request_id
    assert root.arrival_sequence == req.arrival_sequence and root.units_remaining == 2
    # new stock arrives -> the next call finishes the request
    add_bag(db, state, "B2", "B+", 6)
    add_bag(db, state, "B3", "B+", 7)
    result = process_next_request(db, state)
    assert result["result"] == "fulfilled" and result["units_remaining"] == 0
    assert len(state.request_heap) == 0


def test_no_stock_request_stays_pending_with_shortage(db, state):
    req = add_request(db, state, "AB-", 2, 1)
    result = process_next_request(db, state)
    assert result["result"] == "no_stock" and "Shortage" in result["summary"]
    assert db.get(HospitalRequest, req.id).status == "pending"
    assert len(state.request_heap) == 1                      # not lost
    assert db.query(Dispatch).one().result == "no_stock"


def test_blocked_high_priority_request_does_not_starve_others(db, state):
    blocked = add_request(db, state, "AB-", 1, 1)            # critical, but no stock at all
    add_bag(db, state, "B1", "A+", 4)
    ok = add_request(db, state, "A+", 1, 3)                  # routine, can be served
    result = process_next_request(db, state)
    assert result["request"]["request_id"] == ok.request_id
    assert [s["request_id"] for s in result["skipped_requests"]] == [blocked.request_id]
    assert db.get(HospitalRequest, blocked.id).status == "pending"
    assert state.request_heap.peek().request_id == blocked.request_id


def test_critical_request_is_processed_before_earlier_routine(db, state):
    add_bag(db, state, "B1", "A+", 4)
    routine = add_request(db, state, "A+", 1, 3)
    critical = add_request(db, state, "A+", 1, 1)
    result = process_next_request(db, state)
    assert result["request"]["request_id"] == critical.request_id
    assert db.get(HospitalRequest, routine.id).status == "pending"


def test_only_one_request_is_processed_per_call(db, state):
    for i in range(4):
        add_bag(db, state, f"B{i}", "A+", 3 + i)
    first = add_request(db, state, "A+", 1, 2)
    second = add_request(db, state, "A+", 1, 2)
    process_next_request(db, state)
    assert db.get(HospitalRequest, first.id).status == "fulfilled"
    assert db.get(HospitalRequest, second.id).status == "pending"
    assert db.query(Dispatch).count() == 1


def test_each_bag_is_dispatched_at_most_once(db, state):
    add_bag(db, state, "ONLY", "A+", 3)
    add_request(db, state, "A+", 1, 1)
    add_request(db, state, "A+", 1, 1)
    first = process_next_request(db, state)
    second = process_next_request(db, state)
    assert first["allocated_bags"][0]["bag_id"] == "ONLY"
    assert second["result"] == "no_stock" and second["allocated_bags"] == []


def test_fulfilled_and_cancelled_requests_cannot_be_processed_again(db, state):
    add_bag(db, state, "B1", "A+", 3)
    done = add_request(db, state, "A+", 1, 1)
    process_next_request(db, state)
    cancelled = add_request(db, state, "A+", 1, 1)
    row = db.get(HospitalRequest, cancelled.id)
    row.status = "cancelled"
    db.commit()
    # stale heap entries for both requests (as if the heap had not been updated)
    state.request_heap.insert(RequestEntry(done.request_id, 1, done.arrival_sequence, 1))
    with pytest.raises(NoWaitingRequests):
        process_next_request(db, state)


def test_nothing_waiting_raises(db, state):
    with pytest.raises(NoWaitingRequests):
        process_next_request(db, state)


def test_database_failure_gives_no_false_success_and_state_is_restored(db, state, monkeypatch):
    add_bag(db, state, "B1", "A+", 3)
    req = add_request(db, state, "A+", 1, 1)

    def failing_commit():
        raise RuntimeError("disk full")

    monkeypatch.setattr(db, "commit", failing_commit)
    with pytest.raises(RuntimeError):
        process_next_request(db, state)
    monkeypatch.undo()

    assert bag_status(db, "B1") == "available"                       # rolled back
    assert db.get(HospitalRequest, req.id).status == "pending"
    assert db.query(Dispatch).count() == 0
    assert state.fefo.count("A+") == 1                               # heaps rebuilt from the database
    assert state.request_heap.peek().request_id == req.request_id


def test_dispatch_log_is_written_with_items(db, state):
    add_bag(db, state, "B1", "O-", 3)
    add_request(db, state, "O-", 1, 1)
    process_next_request(db, state)
    dispatch = db.query(Dispatch).one()
    assert dispatch.result == "fulfilled" and [i.bag.bag_id for i in dispatch.items] == ["B1"]
    assert "FEFO" in dispatch.decision_summary
