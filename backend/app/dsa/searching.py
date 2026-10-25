"""
Linear Search and Binary Search on arrays.

Linear search : works on ANY array (sorted or not).            O(n)
Binary search : PRECONDITION - the array must be sorted by the exact key being searched.
                Each step halves the search range.              O(log n)

Binary search is never run on a heap's internal array (a heap is only partially ordered)
and `binary_search` refuses unsorted input instead of silently returning a wrong answer.
"""
from dataclasses import dataclass


class UnsortedInputError(ValueError):
    """Raised when binary search is asked to run on an array that is not sorted."""


@dataclass
class SearchResult:
    index: int            # position in the array, -1 if not found
    comparisons: int

    @property
    def found(self):
        return self.index >= 0


def linear_search(items, target, key=lambda x: x):
    comparisons = 0
    for i, item in enumerate(items):
        comparisons += 1
        if key(item) == target:
            return SearchResult(i, comparisons)
    return SearchResult(-1, comparisons)


def is_sorted(items, key=lambda x: x):
    return all(key(items[i]) <= key(items[i + 1]) for i in range(len(items) - 1))


def binary_search(items, target, key=lambda x: x, verify_sorted=True):
    """
    `items` must be sorted ascending by `key`.
    verify_sorted=True checks that precondition first (an O(n) check, reported separately
    from the O(log n) search so the cost is not hidden).
    """
    if verify_sorted and not is_sorted(items, key):
        raise UnsortedInputError("binary search requires an array sorted by the search key")

    comparisons = 0
    low, high = 0, len(items) - 1
    while low <= high:
        mid = (low + high) // 2
        comparisons += 1
        mid_key = key(items[mid])
        if mid_key == target:
            return SearchResult(mid, comparisons)
        if mid_key < target:
            low = mid + 1                  # target can only be in the right half
        else:
            high = mid - 1                 # target can only be in the left half
    return SearchResult(-1, comparisons)
