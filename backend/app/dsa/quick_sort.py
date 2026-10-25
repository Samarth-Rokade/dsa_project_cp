"""
Quick Sort (divide and conquer, in-place, NOT stable).

Idea: pick a pivot, partition the array so that smaller items are on its left and larger
items on its right (the pivot is then in its final position), and sort both sides.

Pivot choice: MEDIAN-OF-THREE (first, middle, last element). This avoids the classic
worst case on already-sorted input, which a naive "always take the last element" pivot
would hit.
Partition scheme: Lomuto.
Recursion depth: we recurse into the SMALLER side and loop on the larger side, so the call
stack never grows deeper than O(log n).

Complexity: average O(n log n), WORST CASE O(n^2) (e.g. many equal keys / unlucky pivots).
Space: O(log n) stack, no extra array (apart from the copy we sort so the input is untouched).
Not stable: equal keys may change order - callers use (value, bag_id) tuples as keys so
the final order is still deterministic.
"""
from .merge_sort import SortResult


def quick_sort(items, key=lambda x: x, reverse=False):
    arr = list(items)
    stats = {"comparisons": 0, "swaps": 0}

    def before(a, b):
        """Strictly before: used to decide which side of the pivot an item belongs to."""
        stats["comparisons"] += 1
        if reverse:
            return key(a) > key(b)
        return key(a) < key(b)

    def swap(i, j):
        if i != j:
            arr[i], arr[j] = arr[j], arr[i]
            stats["swaps"] += 1

    def median_of_three(lo, hi):
        mid = (lo + hi) // 2
        # order the three positions so that arr[lo] <= arr[mid] <= arr[hi] (in sort order)
        if before(arr[mid], arr[lo]):
            swap(mid, lo)
        if before(arr[hi], arr[lo]):
            swap(hi, lo)
        if before(arr[hi], arr[mid]):
            swap(hi, mid)
        return mid                          # now holds the median

    def partition(lo, hi):
        pivot_index = median_of_three(lo, hi)
        swap(pivot_index, hi)               # park the pivot at the end
        pivot = arr[hi]
        boundary = lo - 1                   # everything <= boundary is "before pivot"
        for j in range(lo, hi):
            if before(arr[j], pivot):
                boundary += 1
                swap(boundary, j)
        swap(boundary + 1, hi)              # put the pivot between the two parts
        return boundary + 1

    def sort(lo, hi):
        while lo < hi:
            p = partition(lo, hi)
            if p - lo < hi - p:             # recurse on the smaller part only
                sort(lo, p - 1)
                lo = p + 1
            else:
                sort(p + 1, hi)
                hi = p - 1

    sort(0, len(arr) - 1)
    return SortResult(arr, stats["comparisons"], stats["swaps"])
