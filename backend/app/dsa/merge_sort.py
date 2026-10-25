"""
Merge Sort (divide and conquer, recursive, STABLE).

Idea: split the array in half, sort each half recursively, then merge the two sorted
halves by repeatedly taking the smaller front element.

Complexity: O(n log n) time in every case, O(n) extra space for the merge buffers.
Stable: equal keys keep their original relative order (we take from the LEFT half on ties).

`key` extracts the value to compare. `reverse=True` sorts in descending order.
The original list is never modified - a new sorted list is returned.
"""
from dataclasses import dataclass


@dataclass
class SortResult:
    items: list
    comparisons: int
    data_moves: int          # elements copied into the output buffers


def merge_sort(items, key=lambda x: x, reverse=False):
    stats = {"comparisons": 0, "moves": 0}

    def goes_first(left, right):
        """True if `left` may be placed before `right` (ties go to left => stable)."""
        stats["comparisons"] += 1
        if reverse:
            return key(left) >= key(right)
        return key(left) <= key(right)

    def merge(left, right):
        merged = []
        i = j = 0
        while i < len(left) and j < len(right):
            if goes_first(left[i], right[j]):
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
            stats["moves"] += 1
        # one side is exhausted: copy what is left of the other
        while i < len(left):
            merged.append(left[i])
            i += 1
            stats["moves"] += 1
        while j < len(right):
            merged.append(right[j])
            j += 1
            stats["moves"] += 1
        return merged

    def sort(arr):
        if len(arr) <= 1:                  # base case of the recursion
            return arr
        mid = len(arr) // 2
        return merge(sort(arr[:mid]), sort(arr[mid:]))

    result = sort(list(items))
    return SortResult(result, stats["comparisons"], stats["moves"])
