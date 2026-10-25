"""
Request priority rules (the ONE comparator used by the request heap).

Order:
    1. smaller urgency number first   (1 Critical, 2 Surgery, 3 Routine)
    2. earlier arrival sequence first (first come, first served inside the same urgency)
    3. request id                     (deterministic final tie-breaker)

Because "1 = most urgent", this is a MIN-heap on the tuple (urgency, arrival, request_id).
"""
from dataclasses import dataclass

from ..dsa.binary_heap import BinaryHeap


@dataclass(frozen=True)
class RequestEntry:
    request_id: str
    urgency_level: int
    arrival_sequence: int
    units_remaining: int = 0


def priority_key(entry):
    return (entry.urgency_level, entry.arrival_sequence, entry.request_id)


def request_comes_first(a, b):
    """Comparator handed to BinaryHeap: should request a be processed before request b?"""
    return priority_key(a) < priority_key(b)


def new_request_heap(entries=None):
    return BinaryHeap(request_comes_first, entries)
