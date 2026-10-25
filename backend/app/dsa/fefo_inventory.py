"""
FEFO (First-Expired-First-Out) inventory.

One custom min-heap PER BLOOD GROUP, ordered by (expiry_date, bag_id).
The root of each heap is therefore the bag of that group that will expire first.

To pick stock for a request we may consider several donor groups, so we look at the
root of each eligible heap and take the smallest one (a tiny k-way merge, k <= 8).

Expiry rule: a bag is usable up to and including its expiry date.
It is expired when expiry_date < today.

Complexity
    add_bag                        O(log n)
    peek earliest of one group     O(1)
    pop earliest of one group      O(log n)
    pop earliest among k groups    O(k + log n)
    purge_expired                  O(log n) per removed bag (+ O(1) to check each root)
    rebuild from n bags            O(n)   (heapify per group)
"""
from dataclasses import dataclass
from datetime import date

from .binary_heap import BinaryHeap


@dataclass(frozen=True)
class BagEntry:
    bag_id: str
    blood_group: str
    expiry_date: date


def bag_expires_first(a, b):
    """Comparator for FEFO: earlier expiry first, then smaller bag id."""
    return (a.expiry_date, a.bag_id) < (b.expiry_date, b.bag_id)


class FefoInventory:
    def __init__(self, groups):
        self._groups = list(groups)
        self._heaps = {g: BinaryHeap(bag_expires_first) for g in self._groups}

    # ---------- building ----------
    def add_bag(self, entry):
        self._heaps[entry.blood_group].insert(entry)

    def rebuild(self, entries):
        """Throw everything away and rebuild from the database rows. O(n)."""
        buckets = {g: [] for g in self._groups}
        for e in entries:
            buckets[e.blood_group].append(e)
        for g in self._groups:
            self._heaps[g].build_heap(buckets[g])

    # ---------- queries ----------
    def count(self, group):
        return len(self._heaps[group])

    def count_in(self, groups):
        return sum(len(self._heaps[g]) for g in groups)

    def peek_earliest(self, group):
        return self._heaps[group].peek()

    def snapshot(self):
        """{group: heap array} - used by the DSA Lab to draw the real heaps."""
        return {g: self._heaps[g].to_list() for g in self._groups}

    # ---------- allocation ----------
    def purge_expired(self, today, groups=None):
        """
        Remove every expired bag from the heaps and return them.
        Only the root needs checking: if the root is not expired, nothing below it is
        (children never expire earlier than their parent).
        """
        removed = []
        for g in (groups or self._groups):
            heap = self._heaps[g]
            while not heap.is_empty() and heap.peek().expiry_date < today:
                removed.append(heap.extract())
        return removed

    def peek_earliest_among(self, groups):
        best = None
        for g in groups:
            root = self._heaps[g].peek()
            if root is not None and (best is None or bag_expires_first(root, best)):
                best = root
        return best

    def pop_earliest_among(self, groups):
        """Remove and return the bag with the earliest expiry across `groups`."""
        best = self.peek_earliest_among(groups)
        if best is None:
            return None
        return self._heaps[best.blood_group].extract()
