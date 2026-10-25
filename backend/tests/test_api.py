"""API-level tests (validation, dashboard numbers, full workflow on the seeded demo data)."""
from datetime import date, timedelta

from app.seed import seed_demo_data

TODAY = date.today()


def bag_payload(**overrides):
    body = {
        "blood_group": "A+",
        "collection_date": (TODAY - timedelta(days=5)).isoformat(),
        "expiry_date": (TODAY + timedelta(days=30)).isoformat(),
        "volume_ml": 450,
        "location": "Central Blood Bank",
    }
    body.update(overrides)
    return body


def request_payload(**overrides):
    body = {"hospital_name": "Demo Hospital", "required_blood_group": "A+", "units_needed": 2, "urgency_level": 2}
    body.update(overrides)
    return body


# ---------- validation ----------
def test_invalid_blood_group_rejected(client):
    r = client.post("/api/inventory", json=bag_payload(blood_group="Z+"))
    assert r.status_code == 422 and "blood_group" in r.json()["error"]["fields"]
    r = client.post("/api/requests", json=request_payload(required_blood_group="X"))
    assert r.status_code == 422


def test_expiry_must_be_after_collection(client):
    r = client.post("/api/inventory", json=bag_payload(expiry_date=(TODAY - timedelta(days=9)).isoformat()))
    assert r.status_code == 422
    assert "later than" in r.json()["error"]["fields"]["request"]


def test_duplicate_bag_id_rejected(client):
    assert client.post("/api/inventory", json=bag_payload(bag_id="bag-5000")).status_code == 201
    r = client.post("/api/inventory", json=bag_payload(bag_id="BAG-5000"))
    assert r.status_code == 409 and "bag_id" in r.json()["error"]["fields"]


def test_bag_id_is_generated_when_blank(client):
    first = client.post("/api/inventory", json=bag_payload()).json()
    second = client.post("/api/inventory", json=bag_payload()).json()
    assert first["bag_id"] == "BAG-1001" and second["bag_id"] == "BAG-1002"


def test_invalid_urgency_and_units_rejected(client):
    for bad in ({"urgency_level": 4}, {"urgency_level": 0}, {"units_needed": 0}, {"units_needed": -3},
                {"units_needed": 1.5}):
        assert client.post("/api/requests", json=request_payload(**bad)).status_code == 422


def test_unknown_resources_return_404(client):
    assert client.get("/api/inventory/NOPE-1").status_code == 404
    assert client.get("/api/requests/REQ-9999").status_code == 404
    assert client.get("/api/dispatches/999").status_code == 404


# ---------- workflow ----------
def test_dashboard_metrics_change_with_actions(client):
    kpis = lambda: client.get("/api/analytics/dashboard").json()["kpis"]
    assert kpis()["available_units"] == 0 and kpis()["pending_requests"] == 0

    client.post("/api/inventory", json=bag_payload(bag_id="BAG-7001"))
    assert kpis()["available_units"] == 1 and kpis()["registered_bags"] == 1

    client.post("/api/requests", json=request_payload(urgency_level=1, units_needed=1))
    k = kpis()
    assert k["pending_requests"] == 1 and k["critical_waiting"] == 1

    assert client.post("/api/requests/process-next").status_code == 200
    k = kpis()
    assert k["available_units"] == 0 and k["pending_requests"] == 0 and k["dispatched_units"] == 1
    assert len(client.get("/api/analytics/dashboard").json()["recent_dispatches"]) == 1


def test_expiring_soon_uses_configurable_threshold(client):
    client.post("/api/inventory", json=bag_payload(expiry_date=(TODAY + timedelta(days=10)).isoformat()))
    assert client.get("/api/analytics/dashboard").json()["kpis"]["expiring_soon"] == 0
    client.put("/api/settings", json={"expiring_soon_days": 14})
    assert client.get("/api/analytics/dashboard").json()["kpis"]["expiring_soon"] == 1


def test_process_next_with_empty_queue_returns_409(client):
    r = client.post("/api/requests/process-next")
    assert r.status_code == 409 and "no waiting requests" in r.json()["error"]["message"].lower()


def test_cancel_rules(client):
    created = client.post("/api/requests", json=request_payload()).json()
    assert client.patch(f"/api/requests/{created['request_id']}/cancel").json()["status"] == "cancelled"
    assert client.patch(f"/api/requests/{created['request_id']}/cancel").status_code == 409
    assert client.post("/api/requests/process-next").status_code == 409         # nothing left to process
    assert client.get("/api/requests/queue").json()["count"] == 0


def test_inventory_filter_sort_and_effective_expiry(client, db, state):
    seed_demo_data(db)
    state.rebuild(db)
    data = client.get("/api/inventory", params={"status": "expired"}).json()
    assert {b["bag_id"] for b in data["items"]} == {"BAG-1003", "BAG-1004"}      # row 'available' but past date counts

    for algo in ("merge", "quick"):
        items = client.get("/api/inventory", params={"sort_by": "expiry_date", "algorithm": algo}).json()["items"]
        keys = [(b["expiry_date"], b["bag_id"]) for b in items]
        assert keys == sorted(keys)
    desc = client.get("/api/inventory", params={"sort_by": "blood_group", "order": "desc"}).json()
    assert desc["sort"]["algorithm"] == "merge" and desc["sort"]["comparisons"] > 0

    only_o = client.get("/api/inventory", params={"blood_group": "O-", "search": "bag-100"}).json()
    assert all(b["blood_group"] == "O-" for b in only_o["items"])


def test_bag_updates_and_terminal_states(client, db, state):
    seed_demo_data(db)
    state.rebuild(db)
    ok = client.patch("/api/inventory/BAG-1001", json={"location": "New Branch"})
    assert ok.status_code == 200 and ok.json()["location"] == "New Branch"
    assert client.patch("/api/inventory/BAG-1001", json={"status": "discarded"}).json()["status"] == "discarded"
    assert client.patch("/api/inventory/BAG-1001", json={"location": "x"}).status_code == 409     # terminal
    assert client.patch("/api/inventory/BAG-1014", json={"location": "x"}).status_code == 409     # dispatched
    assert client.patch("/api/inventory/BAG-1003", json={"location": "x"}).status_code == 409     # expired
    # a discarded bag never reaches the allocation heaps again
    assert "BAG-1001" not in [e.bag_id for e in state.fefo.snapshot()["O-"]]


def test_full_demo_walkthrough_on_seed_data(client, db, state):
    """The six clicks documented in seed.py give the documented outcomes."""
    seed_demo_data(db)
    state.rebuild(db)

    def click():
        r = client.post("/api/requests/process-next")
        assert r.status_code == 200, r.text
        return r.json()

    c1 = click()
    assert (c1["request"]["request_id"], c1["result"]) == ("REQ-0003", "fulfilled")
    assert [b["bag_id"] for b in c1["allocated_bags"]] == ["BAG-1001", "BAG-1002"]
    assert c1["expired_removed"] == ["BAG-1003"]

    c2 = click()
    assert c2["request"]["request_id"] == "REQ-0007"
    assert [(b["bag_id"], b["blood_group"]) for b in c2["allocated_bags"]] == [("BAG-1005", "O+")]

    c3 = click()
    assert (c3["request"]["request_id"], c3["result"], c3["units_remaining"]) == ("REQ-0004", "partially_fulfilled", 3)
    assert [b["bag_id"] for b in c3["allocated_bags"]] == ["BAG-1006", "BAG-1011", "BAG-1012", "BAG-1007", "BAG-1016"]

    c4 = click()
    assert (c4["request"]["request_id"], c4["result"]) == ("REQ-0002", "fulfilled")
    assert [b["bag_id"] for b in c4["allocated_bags"]] == ["BAG-1008", "BAG-1009", "BAG-1010"]
    assert {s["request_id"] for s in c4["skipped_requests"]} == {"REQ-0004", "REQ-0005"}

    c5 = click()
    assert (c5["request"]["request_id"], c5["result"]) == ("REQ-0006", "partially_fulfilled")

    c6 = click()
    assert c6["result"] == "no_stock" and c6["shortage_message"]

    history = client.get("/api/dispatches").json()
    assert history["count"] == 7                                                   # 6 clicks + 1 seeded
    assert history["items"][0]["id"] > history["items"][-1]["id"]                  # newest first
    detail = client.get(f"/api/dispatches/{c4['dispatch_id']}").json()
    assert [b["bag_id"] for b in detail["bags"]] == ["BAG-1008", "BAG-1009", "BAG-1010"]
    assert detail["decision_summary"]

    # queue now only holds requests that still need stock
    queue = client.get("/api/requests/queue").json()["items"]
    assert [q["request_id"] for q in queue] == ["REQ-0004", "REQ-0005", "REQ-0006"]


def test_reset_demo_data_restores_seed(client, db, state):
    seed_demo_data(db)
    state.rebuild(db)
    client.post("/api/requests/process-next")
    r = client.post("/api/admin/reset-demo")
    assert r.status_code == 200 and r.json()["dispatches"] == 1
    assert client.get("/api/analytics/dashboard").json()["kpis"]["pending_requests"] == 6


# ---------- DSA Lab ----------
def test_heap_demo_uses_real_heap(client):
    ops = [
        {"op": "insert", "label": "ROUTINE", "urgency_level": 3},
        {"op": "insert", "label": "CRITICAL", "urgency_level": 1},
        {"op": "insert", "label": "SURGERY", "urgency_level": 2},
        {"op": "extract"},
    ]
    data = client.post("/api/dsa/heap-demo", json={"operations": ops}).json()
    assert data["steps"][1]["root"]["label"] == "CRITICAL"
    assert data["steps"][3]["extracted"]["label"] == "CRITICAL"
    assert [e["label"] for e in data["processing_order"]] == ["SURGERY", "ROUTINE"]
    assert data["valid_heap"]


def test_sort_and_search_demos(client, db, state):
    seed_demo_data(db)
    state.rebuild(db)
    for algo in ("merge", "quick"):
        d = client.post("/api/dsa/sort-demo", json={"algorithm": algo, "sort_by": "bag_id"}).json()
        ids = [b["bag_id"] for b in d["after"]]
        assert ids == sorted(ids) and d["comparisons"] > 0
    sample = client.post("/api/dsa/sort-demo", json={"source": "sample", "sample": [3, 1, 2]}).json()
    assert sample["after"] == [1, 2, 3]

    for method in ("linear", "binary", "hash"):
        d = client.post("/api/dsa/search-demo", json={"method": method, "bag_id": "bag-1010"}).json()
        assert d["found"] and d["bag"]["bag_id"] == "BAG-1010"
        miss = client.post("/api/dsa/search-demo", json={"method": method, "bag_id": "NOPE"}).json()
        assert not miss["found"]
    binary = client.post("/api/dsa/search-demo", json={"method": "binary", "bag_id": "BAG-1010"}).json()
    assert binary["sort_comparisons"] > 0 and binary["total_comparisons"] > binary["comparisons"]


def test_hash_demo_shows_collisions(client):
    d = client.post("/api/dsa/hash-demo", json={"keys": [f"K{i}" for i in range(12)], "capacity": 3, "lookup": "K5"}).json()
    assert d["entries"] == 12 and d["collisions"] > 0 and d["lookup"]["found"]
    assert sum(len(b["keys"]) for b in d["buckets"]) == 12


def test_live_structures_and_compatibility_endpoints(client, db, state):
    seed_demo_data(db)
    state.rebuild(db)
    live = client.get("/api/dsa/live").json()
    assert live["request_order"][0]["label"] == "REQ-0003"                          # critical, earliest
    assert live["fefo"]["O-"][0]["label"] in ("BAG-1001", "BAG-1003")
    matrix = client.get("/api/dsa/compatibility").json()
    assert len(matrix["rows"]) == 8 and matrix["mode"] == "educational"


def test_invalid_demo_input_rejected(client):
    assert client.post("/api/dsa/sort-demo", json={"algorithm": "bubble"}).status_code == 422
    assert client.post("/api/dsa/heap-demo", json={"operations": [{"op": "insert"}] * 61}).status_code == 422
    assert client.post("/api/dsa/search-demo", json={"method": "magic", "bag_id": "x"}).status_code == 422
