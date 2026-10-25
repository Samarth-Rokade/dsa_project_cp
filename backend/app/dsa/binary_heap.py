"""
Binary Heap (array representation of a complete binary tree).

A heap is a complete binary tree stored in a plain array. For a node at index i:
    parent = (i - 1) // 2        left child = 2*i + 1        right child = 2*i + 2

Heap invariant (min-heap w.r.t. the `less` function):
    for every node, NOT less(node, parent)   ->   the "best" item is always at index 0.

`less(a, b)` answers: "should a come out BEFORE b?". Because the comparator is passed in,
the same class is used for two different jobs in this project:
    1. Emergency request queue   (urgency, arrival sequence)
    2. FEFO blood stock          (expiry date, bag id)

Complexity
    peek         O(1)
    insert       O(log n)   (sift-up)
    extract      O(log n)   (sift-down)
    build_heap   O(n)       (Floyd's bottom-up heapify)
"""


class BinaryHeap:
    def __init__(self, less, items=None):
        self._data = []
        self._less = less
        # Operation counters - shown in the DSA Lab so the work done is visible.
        self.comparisons = 0
        self.swaps = 0
        if items:
            self.build_heap(items)

    # ---------- index helpers ----------
    @staticmethod
    def parent(i):
        return (i - 1) // 2

    @staticmethod
    def left(i):
        return 2 * i + 1

    @staticmethod
    def right(i):
        return 2 * i + 2

    # ---------- public operations ----------
    def __len__(self):
        return len(self._data)

    def is_empty(self):
        return len(self._data) == 0

    def peek(self):
        """Return the root without removing it. Empty heap -> None.  O(1)"""
        return self._data[0] if self._data else None

    def insert(self, item):
        """Add item at the end, then sift it up until the invariant holds.  O(log n)"""
        self._data.append(item)
        self._sift_up(len(self._data) - 1)

    def extract(self):
        """Remove and return the root. Empty heap -> None.  O(log n)"""
        if not self._data:
            return None
        root = self._data[0]
        last = self._data.pop()
        if self._data:
            self._data[0] = last          # move last leaf to the root ...
            self._sift_down(0)            # ... and push it down to its place
        return root

    def build_heap(self, items):
        """
        Replace the contents with `items` and heapify bottom-up.  O(n)
        Leaves are already valid heaps, so we only sift down the internal nodes,
        from the last parent (n//2 - 1) back to the root.
        """
        self._data = list(items)
        for i in range(len(self._data) // 2 - 1, -1, -1):
            self._sift_down(i)

    def clear(self):
        self._data = []

    def to_list(self):
        """Copy of the internal array (heap order, NOT sorted order)."""
        return list(self._data)

    def sorted_view(self):
        """
        Items in the order they would be extracted, WITHOUT changing this heap.
        Works on a copy of the array.  O(n log n)
        """
        clone = BinaryHeap(self._less)
        clone._data = list(self._data)
        ordered = []
        while not clone.is_empty():
            ordered.append(clone.extract())
        return ordered

    def reset_stats(self):
        self.comparisons = 0
        self.swaps = 0

    def is_valid_heap(self):
        """Check the invariant for every node (used by the unit tests)."""
        for i in range(1, len(self._data)):
            if self._less(self._data[i], self._data[self.parent(i)]):
                return False
        return True

    # ---------- internal helpers ----------
    def _swap(self, i, j):
        self._data[i], self._data[j] = self._data[j], self._data[i]
        self.swaps += 1

    def _sift_up(self, i):
        while i > 0:
            p = self.parent(i)
            self.comparisons += 1
            if self._less(self._data[i], self._data[p]):
                self._swap(i, p)
                i = p
            else:
                break

    def _sift_down(self, i):
        n = len(self._data)
        while True:
            best = i
            l, r = self.left(i), self.right(i)
            if l < n:
                self.comparisons += 1
                if self._less(self._data[l], self._data[best]):
                    best = l
            if r < n:
                self.comparisons += 1
                if self._less(self._data[r], self._data[best]):
                    best = r
            if best == i:
                break
            self._swap(i, best)
            i = best
