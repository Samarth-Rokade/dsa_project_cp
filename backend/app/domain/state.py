"""
In-memory data structures, rebuilt from the database.

The database (SQLite via SQLAlchemy) is the PERSISTENT source of truth.
While the server runs we also keep fast in-memory structures built from it:

    request_heap   BinaryHeap of waiting requests (priority order)
    fefo           one min-heap per blood group, ordered by expiry date
    bag_index      HashTable  bag_id     -> database primary key
    request_index  HashTable  request_id -> database primary key

They are rebuilt from the database on server start (`rebuild`), so nothing is lost on restart.
"""
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import BLOOD_GROUPS, WAITING_STATUSES
from ..dsa.fefo_inventory import BagEntry, FefoInventory
from ..dsa.hash_table import HashTable
from ..models import BloodBag, HospitalRequest
from .priority import RequestEntry, new_request_heap


def bag_to_entry(bag):
    return BagEntry(bag.bag_id, bag.blood_group, bag.expiry_date)


def request_to_entry(req):
    return RequestEntry(
        req.request_id, req.urgency_level, req.arrival_sequence, req.units_needed - req.units_allocated
    )


class InMemoryState:
    def __init__(self):
        self.lock = threading.RLock()          # one allocation / mutation at a time
        self.request_heap = new_request_heap()
        self.fefo = FefoInventory(BLOOD_GROUPS)
        self.bag_index = HashTable()
        self.request_index = HashTable()

    def rebuild(self, db: Session):
        """Rebuild every structure from the database rows."""
        with self.lock:
            bags = list(db.scalars(select(BloodBag)))
            requests = list(db.scalars(select(HospitalRequest)))

            # only bags with status 'available' can ever be allocated
            self.fefo.rebuild([bag_to_entry(b) for b in bags if b.status == "available"])
            self.request_heap.build_heap(
                [request_to_entry(r) for r in requests if r.status in WAITING_STATUSES]
            )

            self.bag_index = HashTable()
            for b in bags:
                self.bag_index.put(b.bag_id, b.id)
            self.request_index = HashTable()
            for r in requests:
                self.request_index.put(r.request_id, r.id)

    # incremental updates (cheaper than a full rebuild)
    def add_bag(self, bag):
        self.bag_index.put(bag.bag_id, bag.id)
        if bag.status == "available":
            self.fefo.add_bag(bag_to_entry(bag))

    def add_request(self, req):
        self.request_index.put(req.request_id, req.id)
        self.request_heap.insert(request_to_entry(req))


# The single instance used by the running application.
state = InMemoryState()


def get_state():
    """FastAPI dependency (tests replace it with a fresh instance)."""
    return state
