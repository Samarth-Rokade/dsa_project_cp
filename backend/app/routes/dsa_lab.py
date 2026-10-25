"""
DSA Lab endpoints.

Every demo here calls the SAME classes/functions the main application uses
(BinaryHeap, FefoInventory, merge_sort, quick_sort, linear_search, binary_search, HashTable).
Algorithm names and input sizes are validated by the Pydantic schemas - no arbitrary code runs.
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import URGENCY_LABELS
from ..database import get_db
from ..domain.compatibility import matrix_for_display
from ..domain.priority import RequestEntry, new_request_heap
from ..domain.settings import get_settings
from ..domain.sorting import COMPLEXITY_NOTES, sort_bags
from ..domain.state import InMemoryState, get_state
from ..dsa.hash_table import HashTable
from ..dsa.merge_sort import merge_sort
from ..dsa.quick_sort import quick_sort
from ..dsa.searching import binary_search, linear_search
from ..models import BloodBag
from ..schemas import HashDemoIn, HeapDemoIn, SearchDemoIn, SortDemoIn
from ..serializers import bag_out

router = APIRouter(prefix="/api/dsa", tags=["DSA Lab"])


def _entry_json(e):
    return {
        "label": e.request_id,
        "urgency_level": e.urgency_level,
        "urgency_label": URGENCY_LABELS[e.urgency_level],
        "arrival_sequence": e.arrival_sequence,
    }


# ---------- request heap ----------
@router.post("/heap-demo")
def heap_demo(body: HeapDemoIn):
    """Replay a list of insert / extract operations on the real request heap and show every step."""
    heap = new_request_heap()
    arrival = 0
    steps = []
    for op in body.operations:
        before_cmp, before_swp = heap.comparisons, heap.swaps
        extracted = None
        if op.op == "insert":
            arrival += 1
            level = op.urgency_level or 3
            label = (op.label or "").strip() or f"R{arrival}"
            entry = RequestEntry(label, level, arrival, 1)
            heap.insert(entry)
            description = f"Insert {label} (urgency {level}, arrival #{arrival}) at the end, then sift up"
        else:
            removed = heap.extract()
            if removed is None:
                description = "Extract on an empty heap returns nothing"
            else:
                extracted = _entry_json(removed)
                description = f"Extract root {removed.request_id}: move the last item to the root, then sift down"
        root = heap.peek()
        steps.append({
            "operation": op.op,
            "description": description,
            "extracted": extracted,
            "array": [_entry_json(e) for e in heap.to_list()],
            "root": _entry_json(root) if root else None,
            "comparisons": heap.comparisons - before_cmp,
            "swaps": heap.swaps - before_swp,
        })
    return {
        "steps": steps,
        "size": len(heap),
        "processing_order": [_entry_json(e) for e in heap.sorted_view()],
        "valid_heap": heap.is_valid_heap(),
    }


# ---------- live structures ----------
@router.get("/live")
def live_structures(state: InMemoryState = Depends(get_state)):
    """The REAL in-memory structures of the running application."""
    return {
        "request_heap": [_entry_json(e) for e in state.request_heap.to_list()],
        "request_order": [_entry_json(e) for e in state.request_heap.sorted_view()],
        "fefo": {
            group: [
                {"label": b.bag_id, "blood_group": b.blood_group, "expiry_date": b.expiry_date.isoformat()}
                for b in entries
            ]
            for group, entries in state.fefo.snapshot().items()
        },
        "bag_index": {
            "entries": len(state.bag_index),
            "capacity": state.bag_index.capacity,
            "load_factor": round(state.bag_index.load_factor, 3),
            "collisions": state.bag_index.collisions,
        },
        "request_index": {
            "entries": len(state.request_index),
            "capacity": state.request_index.capacity,
            "load_factor": round(state.request_index.load_factor, 3),
            "collisions": state.request_index.collisions,
        },
    }


# ---------- sorting ----------
def _compact(bag):
    return {k: bag[k] for k in ("bag_id", "blood_group", "collection_date", "expiry_date", "effective_status")}


@router.post("/sort-demo")
def sort_demo(body: SortDemoIn, db: Session = Depends(get_db)):
    if body.source == "sample":
        numbers = body.sample or [38, 27, 43, 3, 9, 82, 10, 27, 3, 55]
        algorithm = merge_sort if body.algorithm == "merge" else quick_sort
        result = algorithm(numbers, reverse=(body.order == "desc"))
        before, after = numbers, result.items
        truncated = False
    else:
        today = date.today()
        bags = [bag_out(b, today) for b in db.scalars(select(BloodBag).order_by(BloodBag.id).limit(201))]
        truncated = len(bags) > 200
        bags = bags[:200]
        result = sort_bags(bags, body.sort_by, body.order, body.algorithm)
        before, after = [_compact(b) for b in bags], [_compact(b) for b in result.items]
    return {
        "algorithm": body.algorithm,
        "sort_by": body.sort_by if body.source == "inventory" else "value",
        "order": body.order,
        "n": len(before),
        "truncated": truncated,
        "before": before,
        "after": after,
        "comparisons": result.comparisons,
        "data_moves": result.data_moves,
        "moves_label": "elements copied" if body.algorithm == "merge" else "swaps",
        **COMPLEXITY_NOTES[body.algorithm],
    }


# ---------- searching ----------
@router.post("/search-demo")
def search_demo(body: SearchDemoIn, db: Session = Depends(get_db), state: InMemoryState = Depends(get_state)):
    target = body.bag_id.strip().upper()
    today = date.today()
    bags = [bag_out(b, today) for b in db.scalars(select(BloodBag).order_by(BloodBag.id))]
    n = len(bags)

    if body.method == "linear":
        # unsorted snapshot (database order) -> linear search is the right tool
        res = linear_search(bags, target, key=lambda b: b["bag_id"])
        return {
            "method": "linear", "n": n, "target": target, "found": res.found,
            "bag": bags[res.index] if res.found else None,
            "comparisons": res.comparisons, "sort_comparisons": 0,
            "total_comparisons": res.comparisons,
            "precondition": "None - works on unsorted data",
            "complexity": "O(n)",
        }

    if body.method == "binary":
        # binary search needs an array sorted by the SAME key, so sort first and report that cost too
        sorted_bags = merge_sort(bags, key=lambda b: b["bag_id"])
        res = binary_search(sorted_bags.items, target, key=lambda b: b["bag_id"])
        return {
            "method": "binary", "n": n, "target": target, "found": res.found,
            "bag": sorted_bags.items[res.index] if res.found else None,
            "comparisons": res.comparisons, "sort_comparisons": sorted_bags.comparisons,
            "total_comparisons": res.comparisons + sorted_bags.comparisons,
            "precondition": "Array sorted by bag_id (merge sort run first, its cost is included)",
            "complexity": "O(log n) search after an O(n log n) sort",
        }

    pk = state.bag_index.get(target)
    steps = state.bag_index.last_steps
    bag = db.get(BloodBag, pk) if pk is not None else None
    return {
        "method": "hash", "n": n, "target": target, "found": bag is not None,
        "bag": bag_out(bag, today) if bag else None,
        "comparisons": steps, "sort_comparisons": 0, "total_comparisons": steps,
        "precondition": "Hash index built from the bag IDs (no sorting needed)",
        "complexity": "O(1) average, O(n) worst case",
        "bucket": state.bag_index.index_for(target),
    }


# ---------- hash table ----------
@router.post("/hash-demo")
def hash_demo(body: HashDemoIn):
    table = HashTable(capacity=body.capacity, auto_resize=False)    # fixed size so collisions are visible
    keys = [k.strip() for k in body.keys if k.strip()]
    rows = []
    for key in keys:
        table.put(key, True)
        rows.append({"key": key, "hash_code": table.hash_code(key), "bucket": table.index_for(key)})
    lookup = None
    if body.lookup and body.lookup.strip():
        key = body.lookup.strip()
        found = table.contains(key)
        lookup = {
            "key": key, "found": found, "bucket": table.index_for(key),
            "chain_nodes_visited": table.last_steps,
        }
    return {
        "capacity": table.capacity,
        "entries": len(table),
        "load_factor": round(table.load_factor, 3),
        "collisions": table.collisions,
        "buckets": table.bucket_view(),
        "keys": rows,
        "lookup": lookup,
    }


# ---------- compatibility ----------
@router.get("/compatibility")
def compatibility(db: Session = Depends(get_db)):
    mode = get_settings(db)["compatibility_mode"]
    return matrix_for_display(mode)
