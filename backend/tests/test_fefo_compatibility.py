from datetime import date, timedelta

import pytest

from app.constants import BLOOD_GROUPS
from app.domain.compatibility import (
    COMPATIBILITY_MATRIX, RECIPIENT_TO_DONORS, get_compatible_donor_groups,
)
from app.domain.state import InMemoryState
from app.dsa.fefo_inventory import BagEntry, FefoInventory

TODAY = date(2030, 6, 1)


def bag(bag_id, group, days):
    return BagEntry(bag_id, group, TODAY + timedelta(days=days))


# ---------- FEFO ----------
def test_earliest_expiring_bag_comes_out_first():
    fefo = FefoInventory(BLOOD_GROUPS)
    for b in [bag("B1", "A+", 10), bag("B2", "A+", 3), bag("B3", "A+", 7)]:
        fefo.add_bag(b)
    assert fefo.peek_earliest("A+").bag_id == "B2"
    assert [fefo.pop_earliest_among(["A+"]).bag_id for _ in range(3)] == ["B2", "B3", "B1"]
    assert fefo.pop_earliest_among(["A+"]) is None


def test_equal_expiry_uses_bag_id_tiebreaker():
    fefo = FefoInventory(BLOOD_GROUPS)
    fefo.add_bag(bag("B9", "O+", 5))
    fefo.add_bag(bag("B2", "O+", 5))
    assert fefo.pop_earliest_among(["O+"]).bag_id == "B2"
    assert fefo.pop_earliest_among(["O+"]).bag_id == "B9"


def test_earliest_among_several_compatible_groups():
    fefo = FefoInventory(BLOOD_GROUPS)
    fefo.add_bag(bag("A1", "A+", 9))
    fefo.add_bag(bag("O1", "O+", 2))
    fefo.add_bag(bag("N1", "O-", 4))
    fefo.add_bag(bag("X1", "B+", 1))                      # not in the eligible list
    order = [fefo.pop_earliest_among(["A+", "A-", "O+", "O-"]).bag_id for _ in range(3)]
    assert order == ["O1", "N1", "A1"]
    assert fefo.count("B+") == 1                          # untouched


def test_expired_bags_are_purged_and_never_returned():
    fefo = FefoInventory(BLOOD_GROUPS)
    fefo.add_bag(bag("OLD", "A+", -1))
    fefo.add_bag(bag("OLDER", "A+", -9))
    fefo.add_bag(bag("TODAY", "A+", 0))                    # expiry date == today is still usable
    fefo.add_bag(bag("FRESH", "A+", 5))
    removed = fefo.purge_expired(TODAY)
    assert sorted(b.bag_id for b in removed) == ["OLD", "OLDER"]
    assert fefo.pop_earliest_among(["A+"]).bag_id == "TODAY"


def test_new_bag_appears_in_correct_group_structure():
    fefo = FefoInventory(BLOOD_GROUPS)
    fefo.add_bag(bag("N1", "AB-", 4))
    assert fefo.count("AB-") == 1 and fefo.count("AB+") == 0
    assert fefo.snapshot()["AB-"][0].bag_id == "N1"


def test_rebuild_from_entries():
    fefo = FefoInventory(BLOOD_GROUPS)
    fefo.add_bag(bag("OLD", "A+", 1))
    fefo.rebuild([bag("N1", "B+", 8), bag("N2", "B+", 3)])
    assert fefo.count("A+") == 0 and fefo.count("B+") == 2
    assert fefo.peek_earliest("B+").bag_id == "N2"


def test_structures_rebuild_from_database_after_restart(db, state):
    from tests.conftest import add_bag, add_request
    add_bag(db, state, "B-1", "A+", 5)
    add_bag(db, state, "B-2", "A+", 2)
    add_bag(db, state, "B-3", "A+", 9, status="dispatched")      # never enters the FEFO heap
    add_request(db, state, "A+", 1, 3)
    add_request(db, state, "A+", 1, 1)

    restarted = InMemoryState()                                   # simulates a fresh server process
    restarted.rebuild(db)
    assert restarted.fefo.count("A+") == 2
    assert restarted.fefo.peek_earliest("A+").bag_id == "B-2"
    assert restarted.request_heap.peek().request_id == "REQ-0002"  # the critical one
    assert restarted.bag_index.get("B-1") is not None
    assert restarted.request_index.get("REQ-0001") is not None


# ---------- compatibility ----------
def test_all_eight_groups_have_a_result():
    for group in BLOOD_GROUPS:
        donors = get_compatible_donor_groups(group)
        assert donors and group in donors


def test_direction_is_requested_group_to_donor_groups():
    assert get_compatible_donor_groups("AB+") == ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    assert get_compatible_donor_groups("O-") == ["O-"]                  # O- recipients accept only O-
    assert get_compatible_donor_groups("A+") == ["A+", "A-", "O+", "O-"]
    assert get_compatible_donor_groups("B-") == ["B-", "O-"]
    # O- stock is eligible for every request (broad donor group)
    assert all("O-" in get_compatible_donor_groups(g) for g in BLOOD_GROUPS)
    # AB+ stock is eligible only for AB+ requests
    assert [g for g in BLOOD_GROUPS if "AB+" in get_compatible_donor_groups(g)] == ["AB+"]


def test_ineligible_groups_are_excluded():
    assert "B+" not in get_compatible_donor_groups("A+")
    assert "A+" not in get_compatible_donor_groups("A-")           # Rh-positive blood to Rh-negative: no
    assert "AB-" not in get_compatible_donor_groups("O+")


def test_exact_mode_only_matches_same_group():
    for group in BLOOD_GROUPS:
        assert get_compatible_donor_groups(group, mode="exact") == [group]


def test_unknown_group_is_rejected():
    with pytest.raises(ValueError):
        get_compatible_donor_groups("C+")


def test_matrix_is_8x8_and_matches_lookup():
    assert len(COMPATIBILITY_MATRIX) == 8 and all(len(row) == 8 for row in COMPATIBILITY_MATRIX)
    for r, recipient in enumerate(BLOOD_GROUPS):
        allowed = [BLOOD_GROUPS[c] for c in range(8) if COMPATIBILITY_MATRIX[r][c]]
        assert sorted(allowed) == sorted(RECIPIENT_TO_DONORS[recipient])
