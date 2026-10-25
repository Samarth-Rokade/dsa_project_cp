import random

import pytest

from app.dsa.hash_table import HashTable
from app.dsa.merge_sort import merge_sort
from app.dsa.quick_sort import quick_sort
from app.dsa.searching import UnsortedInputError, binary_search, linear_search

SORTS = [merge_sort, quick_sort]


@pytest.mark.parametrize("sort", SORTS)
def test_ascending_and_descending(sort):
    data = [5, 2, 9, 1, 5, 6, 0, -3]
    assert sort(data).items == sorted(data)
    assert sort(data, reverse=True).items == sorted(data, reverse=True)


@pytest.mark.parametrize("sort", SORTS)
def test_empty_single_and_already_sorted(sort):
    assert sort([]).items == []
    assert sort([7]).items == [7]
    assert sort([1, 2, 3, 4]).items == [1, 2, 3, 4]
    assert sort([4, 3, 2, 1]).items == [1, 2, 3, 4]


@pytest.mark.parametrize("sort", SORTS)
def test_input_list_is_not_modified(sort):
    data = [3, 1, 2]
    sort(data)
    assert data == [3, 1, 2]


@pytest.mark.parametrize("sort", SORTS)
def test_matches_trusted_result_on_random_data(sort):
    rng = random.Random(7)
    for _ in range(50):
        data = [rng.randint(0, 30) for _ in range(rng.randint(0, 60))]
        assert sort(data).items == sorted(data)
        assert sort(data, reverse=True).items == sorted(data, reverse=True)


@pytest.mark.parametrize("sort", SORTS)
def test_duplicate_keys_are_deterministic_with_tiebreaker(sort):
    bags = [
        {"bag_id": "B3", "expiry": "2030-01-05"},
        {"bag_id": "B1", "expiry": "2030-01-05"},
        {"bag_id": "B2", "expiry": "2030-01-01"},
    ]
    result = sort(bags, key=lambda b: (b["expiry"], b["bag_id"])).items
    assert [b["bag_id"] for b in result] == ["B2", "B1", "B3"]


def test_merge_sort_is_stable():
    items = [("a", 1), ("b", 1), ("c", 0), ("d", 1), ("e", 0)]
    result = merge_sort(items, key=lambda x: x[1]).items
    assert [x[0] for x in result] == ["c", "e", "a", "b", "d"]
    # descending is stable too
    result = merge_sort(items, key=lambda x: x[1], reverse=True).items
    assert [x[0] for x in result] == ["a", "b", "d", "c", "e"]


def test_quick_sort_survives_large_sorted_and_equal_inputs():
    assert quick_sort(list(range(3000))).items == list(range(3000))
    assert quick_sort([5] * 800).items == [5] * 800          # many equal keys (still correct)


def test_sorts_report_operation_counts():
    assert merge_sort([3, 2, 1]).comparisons > 0
    assert quick_sort([3, 2, 1]).comparisons > 0


# ---------- searching ----------
def test_linear_search_on_unsorted_array():
    data = [40, 7, 19, 3]
    assert linear_search(data, 19).index == 2
    assert linear_search(data, 19).comparisons == 3
    result = linear_search(data, 99)
    assert result.index == -1 and not result.found and result.comparisons == 4


def test_linear_search_with_key():
    bags = [{"bag_id": "B2"}, {"bag_id": "B1"}]
    assert linear_search(bags, "B1", key=lambda b: b["bag_id"]).index == 1


def test_binary_search_found_and_not_found():
    data = [1, 3, 5, 7, 9, 11]
    for i, value in enumerate(data):
        assert binary_search(data, value).index == i
    assert binary_search(data, 4).index == -1
    assert binary_search([], 1).index == -1


def test_binary_search_needs_few_comparisons():
    data = list(range(1024))
    assert binary_search(data, 777).comparisons <= 11          # about log2(1024) + 1


def test_binary_search_refuses_unsorted_array():
    with pytest.raises(UnsortedInputError):
        binary_search([3, 1, 2], 1)


def test_binary_search_after_sorting_by_same_key():
    bags = [{"bag_id": "B3"}, {"bag_id": "B1"}, {"bag_id": "B2"}]
    ordered = merge_sort(bags, key=lambda b: b["bag_id"]).items
    assert binary_search(ordered, "B3", key=lambda b: b["bag_id"]).index == 2


# ---------- hash table ----------
def test_hash_put_get_update_delete():
    table = HashTable(capacity=5)
    table.put("BAG-1", 10)
    table.put("BAG-2", 20)
    assert table.get("BAG-1") == 10
    table.put("BAG-1", 11)                       # update, size unchanged
    assert table.get("BAG-1") == 11 and len(table) == 2
    assert table.delete("BAG-1") is True
    assert table.get("BAG-1") is None
    assert table.delete("BAG-1") is False
    assert not table.contains("BAG-1") and table.contains("BAG-2")


def test_hash_collisions_are_handled_by_chaining():
    table = HashTable(capacity=1, auto_resize=False)         # everything lands in bucket 0
    for i in range(6):
        table.put(f"K{i}", i)
    assert table.collisions == 5
    assert all(table.get(f"K{i}") == i for i in range(6))
    assert table.bucket_view()[0]["keys"].__len__() == 6
    assert table.delete("K3") and table.get("K3") is None and len(table) == 5


def test_hash_resize_keeps_all_entries():
    table = HashTable(capacity=2, max_load=0.75)
    for i in range(50):
        table.put(f"K{i}", i)
    assert table.capacity > 2 and len(table) == 50
    assert all(table.get(f"K{i}") == i for i in range(50))
    assert table.load_factor <= 0.75


def test_hash_function_is_deterministic():
    assert HashTable.hash_code("BAG-1001") == HashTable.hash_code("BAG-1001")
    assert HashTable.hash_code("BAG-1001") != HashTable.hash_code("BAG-1002")
