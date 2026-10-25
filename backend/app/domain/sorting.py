"""Sort keys for inventory records + a switch between the two custom sorting algorithms."""
from ..constants import BLOOD_GROUPS
from ..dsa.merge_sort import merge_sort
from ..dsa.quick_sort import quick_sort

# Every key ends with bag_id so equal values are ordered deterministically.
BAG_SORT_KEYS = {
    "expiry_date": lambda b: (b["expiry_date"], b["bag_id"]),
    "collection_date": lambda b: (b["collection_date"], b["bag_id"]),
    "blood_group": lambda b: (BLOOD_GROUPS.index(b["blood_group"]), b["bag_id"]),
    "bag_id": lambda b: b["bag_id"],
}

ALGORITHMS = {"merge": merge_sort, "quick": quick_sort}

COMPLEXITY_NOTES = {
    "merge": {
        "name": "Merge Sort",
        "time": "O(n log n) in best, average and worst case",
        "space": "O(n) extra space",
        "stable": True,
    },
    "quick": {
        "name": "Quick Sort (median-of-three pivot)",
        "time": "Average O(n log n), worst case O(n^2)",
        "space": "O(log n) stack space (sorts in place)",
        "stable": False,
    },
}


def sort_bags(bags, sort_by="expiry_date", order="asc", algorithm="merge"):
    """Sort a list of bag dictionaries with OUR merge/quick sort (not Python's sorted())."""
    return ALGORITHMS[algorithm](bags, key=BAG_SORT_KEYS[sort_by], reverse=(order == "desc"))
