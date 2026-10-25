"""
Hash Table with SEPARATE CHAINING (also called open hashing).

    table = array of buckets;   each bucket = a singly linked chain of (key, value) nodes.

Hash function (djb2, deterministic for strings):
    h = 5381;  for each character c:  h = h * 33 + ord(c)      (kept to 32 bits)
    bucket index = h % capacity

Collision: two different keys land in the same bucket (synonyms). We simply add the new
node to the front of that bucket's chain, so nothing is overwritten.

Resizing: when load factor (entries / buckets) goes above `max_load` the table doubles
its capacity and re-inserts (rehashes) every entry, keeping chains short.

Complexity: insert / get / delete are O(1) on average, O(n) in the worst case
(all keys in one chain).
"""


class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, next_node=None):
        self.key = key
        self.value = value
        self.next = next_node


class HashTable:
    def __init__(self, capacity=16, max_load=0.75, auto_resize=True):
        self._capacity = max(1, capacity)
        self._buckets = [None] * self._capacity
        self._size = 0
        self._max_load = max_load
        self._auto_resize = auto_resize
        self.collisions = 0          # inserts that landed in an already used bucket
        self.last_steps = 0          # chain nodes visited by the most recent operation

    # ---------- hashing ----------
    @staticmethod
    def hash_code(key):
        h = 5381
        for ch in str(key):
            h = (h * 33 + ord(ch)) & 0xFFFFFFFF
        return h

    def index_for(self, key):
        return self.hash_code(key) % self._capacity

    # ---------- operations ----------
    def put(self, key, value):
        """Insert or update."""
        idx = self.index_for(key)
        node = self._buckets[idx]
        steps = 0
        while node is not None:
            steps += 1
            if node.key == key:                  # key exists -> update
                node.value = value
                self.last_steps = steps
                return
            node = node.next
        if self._buckets[idx] is not None:
            self.collisions += 1
        self._buckets[idx] = _Node(key, value, self._buckets[idx])   # insert at chain head
        self._size += 1
        self.last_steps = steps
        if self._auto_resize and self.load_factor > self._max_load:
            self._resize(self._capacity * 2 + 1)

    def get(self, key, default=None):
        node = self._buckets[self.index_for(key)]
        steps = 0
        while node is not None:
            steps += 1
            if node.key == key:
                self.last_steps = steps
                return node.value
            node = node.next
        self.last_steps = steps
        return default

    def contains(self, key):
        sentinel = object()
        return self.get(key, sentinel) is not sentinel

    def delete(self, key):
        """Remove key. Returns True if it was present."""
        idx = self.index_for(key)
        node, prev = self._buckets[idx], None
        while node is not None:
            if node.key == key:
                if prev is None:
                    self._buckets[idx] = node.next
                else:
                    prev.next = node.next
                self._size -= 1
                return True
            prev, node = node, node.next
        return False

    # ---------- introspection ----------
    def __len__(self):
        return self._size

    @property
    def capacity(self):
        return self._capacity

    @property
    def load_factor(self):
        return self._size / self._capacity

    def keys(self):
        return [k for k, _ in self.items()]

    def items(self):
        out = []
        for head in self._buckets:
            node = head
            while node is not None:
                out.append((node.key, node.value))
                node = node.next
        return out

    def bucket_view(self):
        """[{index, keys:[...chain...]}] - drawn by the DSA Lab."""
        view = []
        for i, head in enumerate(self._buckets):
            chain, node = [], head
            while node is not None:
                chain.append(node.key)
                node = node.next
            view.append({"index": i, "keys": chain})
        return view

    # ---------- internal ----------
    def _resize(self, new_capacity):
        old_items = self.items()
        self._capacity = new_capacity
        self._buckets = [None] * new_capacity
        self._size = 0
        for k, v in old_items:
            self.put(k, v)
