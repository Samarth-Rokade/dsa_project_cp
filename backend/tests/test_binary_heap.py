import random

from app.domain.priority import RequestEntry, new_request_heap, request_comes_first
from app.dsa.binary_heap import BinaryHeap


def req(request_id, urgency, arrival):
    return RequestEntry(request_id, urgency, arrival, 1)


# ---------- generic heap ----------
def test_empty_heap_behaviour():
    heap = BinaryHeap(lambda a, b: a < b)
    assert heap.is_empty()
    assert heap.peek() is None
    assert heap.extract() is None
    assert len(heap) == 0


def test_insert_peek_extract_gives_sorted_order():
    heap = BinaryHeap(lambda a, b: a < b)
    for value in [9, 4, 7, 1, 8, 2, 6]:
        heap.insert(value)
        assert heap.is_valid_heap()
    assert heap.peek() == 1
    assert [heap.extract() for _ in range(7)] == [1, 2, 4, 6, 7, 8, 9]
    assert heap.extract() is None


def test_heap_invariant_after_many_random_operations():
    rng = random.Random(42)
    heap = BinaryHeap(lambda a, b: a < b)
    reference = []
    for _ in range(500):
        if reference and rng.random() < 0.4:
            assert heap.extract() == min(reference)
            reference.remove(min(reference))
        else:
            value = rng.randint(0, 100)
            heap.insert(value)
            reference.append(value)
        assert heap.is_valid_heap()
        assert len(heap) == len(reference)


def test_build_heap_is_valid_and_complete():
    data = [15, 3, 17, 10, 84, 19, 6, 22, 9]
    heap = BinaryHeap(lambda a, b: a < b, data)
    assert heap.is_valid_heap()
    assert heap.peek() == 3
    assert sorted(heap.to_list()) == sorted(data)


def test_sorted_view_does_not_change_heap():
    heap = BinaryHeap(lambda a, b: a < b, [5, 1, 4, 2, 3])
    before = heap.to_list()
    assert heap.sorted_view() == [1, 2, 3, 4, 5]
    assert heap.to_list() == before


def test_operation_counters_increase():
    heap = BinaryHeap(lambda a, b: a < b)
    for value in [3, 2, 1]:
        heap.insert(value)
    assert heap.comparisons > 0 and heap.swaps > 0


# ---------- request priority ----------
def test_critical_request_processed_before_routine_even_if_routine_arrived_first():
    heap = new_request_heap()
    heap.insert(req("REQ-1", urgency=3, arrival=1))     # routine, first to arrive
    heap.insert(req("REQ-2", urgency=1, arrival=2))     # critical, arrived later
    assert heap.extract().request_id == "REQ-2"
    assert heap.extract().request_id == "REQ-1"


def test_equal_urgency_ordered_by_arrival_sequence():
    heap = new_request_heap()
    for rid, arrival in [("REQ-3", 3), ("REQ-1", 1), ("REQ-2", 2)]:
        heap.insert(req(rid, 2, arrival))
    assert [heap.extract().request_id for _ in range(3)] == ["REQ-1", "REQ-2", "REQ-3"]


def test_full_priority_order_urgency_then_arrival_then_id():
    heap = new_request_heap()
    heap.insert(req("B", 2, 5))
    heap.insert(req("A", 2, 5))            # same urgency and arrival -> request id decides
    heap.insert(req("C", 3, 1))
    heap.insert(req("D", 1, 9))
    assert [e.request_id for e in heap.sorted_view()] == ["D", "A", "B", "C"]


def test_comparator_direction():
    assert request_comes_first(req("x", 1, 9), req("y", 2, 1))        # smaller urgency number wins
    assert not request_comes_first(req("y", 2, 1), req("x", 1, 9))
    assert request_comes_first(req("x", 2, 1), req("y", 2, 2))        # earlier arrival wins
