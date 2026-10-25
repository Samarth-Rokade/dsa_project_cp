import { Binary, Grid3x3, Hash, Layers, ListOrdered, Search, SortAsc, Timer } from "lucide-react";
import { PageHead } from "../components/ui.jsx";

const STRUCTURES = [
  {
    icon: ListOrdered, title: "Binary Heap — request priority queue",
    why: "The next request must always be the most urgent one, and new requests keep arriving. A heap gives the best item in O(1) and keeps itself ordered in O(log n).",
    where: "dsa/binary_heap.py · domain/priority.py · POST /api/requests/process-next",
    how: "Complete binary tree stored in an array (children of i at 2i+1 and 2i+2). Insert = add at the end and sift up. Extract = move the last item to the root and sift down. Ordered by (urgency, arrival sequence, request ID).",
    test: "tests/test_binary_heap.py — critical beats routine, ties by arrival, empty heap, random operations keep the invariant.",
  },
  {
    icon: Layers, title: "Per-group Min-Heaps — FEFO stock",
    why: "To reduce expiry waste the bag that expires first must be used first. One heap per blood group keeps the earliest-expiring bag at the root.",
    where: "dsa/fefo_inventory.py · domain/allocation_service.py",
    how: "The same BinaryHeap class with a different comparator: (expiry date, bag ID). For a request we look at the roots of every compatible group and take the smallest (a k-way pick, k ≤ 8). Expired roots are removed before allocating.",
    test: "tests/test_fefo_compatibility.py — earliest expiry first, tie-break by bag ID, expired never allocated, rebuild after restart.",
  },
  {
    icon: Grid3x3, title: "Compatibility matrix — 2-D array lookup",
    why: "Compatibility must be looked up in a table, never guessed from the text of a blood-group name.",
    where: "domain/compatibility.py · shown in DSA Lab → Compatibility",
    how: "8×8 array: row = requested (recipient) group, column = donor stock group. get_compatible_donor_groups reads one row. A second mode allows exact matches only. This is a simplified teaching table.",
    test: "tests/test_fefo_compatibility.py — all 8 groups, direction recipient → donors, ineligible groups excluded.",
  },
  {
    icon: SortAsc, title: "Merge Sort and Quick Sort",
    why: "Inventory lists, request lists and dispatch history must be shown in a chosen order. Two algorithms let us compare stability, memory and worst cases.",
    where: "dsa/merge_sort.py · dsa/quick_sort.py · every sortable table (switch algorithm on the Inventory page)",
    how: "Merge Sort splits, sorts both halves recursively and merges (stable, O(n) extra space). Quick Sort partitions around a median-of-three pivot in place (average O(n log n), worst O(n²), not stable).",
    test: "tests/test_sorting_searching.py — asc/desc, duplicates, stability, random data vs. trusted result.",
  },
  {
    icon: Search, title: "Linear Search and Binary Search",
    why: "Find a bag by ID. Linear search works on any list. Binary search is much faster but only on a list sorted by the same key.",
    where: "dsa/searching.py · Inventory → Exact bag lookup · DSA Lab → Searching",
    how: "Binary search halves the range each step and refuses unsorted input. The lab sorts by bag ID first and reports the sorting cost too, so the cost is not hidden.",
    test: "tests/test_sorting_searching.py — found / not found, empty array, unsorted input rejected.",
  },
  {
    icon: Hash, title: "Hash Table with separate chaining",
    why: "Exact lookups by bag ID or request ID and fast duplicate-ID detection in O(1) on average.",
    where: "dsa/hash_table.py · domain/state.py (bag_index, request_index) · duplicate check on Add bag",
    how: "djb2 string hash modulo the bucket count; each bucket is a chain of linked nodes. Collisions extend the chain; the table doubles when the load factor passes 0.75. It is an in-memory index — the database stays the permanent store.",
    test: "tests/test_sorting_searching.py — put/get/update/delete, forced collisions, resize.",
  },
];

const COMPLEXITY = [
  ["Peek next request", "Binary heap", "O(1)"],
  ["Insert request", "Binary heap", "O(log n)"],
  ["Remove highest-priority request", "Binary heap", "O(log n)"],
  ["Build heap from n items (startup, cancel)", "Bottom-up heapify", "O(n)"],
  ["Peek earliest expiry in one group", "Min-heap", "O(1)"],
  ["Insert / remove one bag", "Min-heap", "O(log n)"],
  ["Linear search", "Array", "O(n)"],
  ["Binary search (after sorting)", "Sorted array", "O(log n)"],
  ["Merge Sort", "Array", "O(n log n) time, O(n) extra space"],
  ["Quick Sort", "Array", "Average O(n log n), worst O(n²)"],
  ["Hash-table lookup", "Chained hash table", "Average O(1), worst O(n)"],
  ["Database queries", "SQLite via SQLAlchemy", "Depends on indexes — not a DSA claim"],
];

export default function About() {
  return (
    <>
      <PageHead
        title="About / DSA Notes"
        subtitle="What the project does, which data structures it uses, and why each one fits."
      />

      <div className="card doc card-body">
        <h2 style={{ marginTop: 0 }}>The problem</h2>
        <p>
          A blood bank holds bags with different blood groups and expiry dates, while hospitals send requests with
          different urgency. The engine decides <b>which request to serve next</b>, <b>which stored bags are allowed</b>,
          and <b>which bags to use first</b> so that stock close to expiry is not wasted.
        </p>
        <h2>How one request is processed</h2>
        <ul>
          <li>Expired bags are removed from the FEFO heaps and marked expired.</li>
          <li>The request heap hands out the most urgent request (ties: earliest arrival).</li>
          <li>The compatibility matrix gives the donor groups that may be used.</li>
          <li>Bags are allocated one by one, always the earliest expiry among those groups (FEFO).</li>
          <li>Bags, request and a dispatch record are saved in one database transaction.</li>
          <li>A partially fulfilled request goes back into the heap with its original arrival position.</li>
        </ul>
      </div>

      <h2 style={{ margin: "26px 0 12px", fontSize: 19, fontWeight: 800 }}>Data structures and algorithms used</h2>
      <div className="grid grid-2">
        {STRUCTURES.map(({ icon: Icon, title, why, where, how, test }) => (
          <div key={title} className="card ds-card">
            <h3><span className="kpi-icon tone-rose" style={{ width: 36, height: 36 }}><Icon size={18} /></span>{title}</h3>
            <dl>
              <dt>Why it fits</dt><dd>{why}</dd>
              <dt>Where used</dt><dd className="mono" style={{ fontSize: 12.5 }}>{where}</dd>
              <dt>How it works</dt><dd>{how}</dd>
              <dt>Verified by</dt><dd>{test}</dd>
            </dl>
          </div>
        ))}
      </div>

      <section className="card" style={{ marginTop: 22 }}>
        <div className="card-head"><h3><Timer size={17} /> Complexity table</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Operation</th><th>Structure / algorithm</th><th>Expected complexity</th></tr></thead>
            <tbody>
              {COMPLEXITY.map(([op, ds, c]) => (
                <tr key={op}><td>{op}</td><td className="muted">{ds}</td><td className="mono bold">{c}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-foot">
          The whole allocation is not O(log n): it checks several compatible groups and may allocate many bags, so its cost depends on the groups and bags actually processed.
        </div>
      </section>

      <div className="grid grid-2" style={{ marginTop: 22 }}>
        <section className="card card-body doc">
          <h3 style={{ marginTop: 0 }}><Binary size={16} style={{ verticalAlign: -3 }} /> Deliberately not included</h3>
          <p>To stay honest about coverage, these topics are <b>not</b> claimed: Heap Sort, BST / threaded trees, BFS / DFS and other graph algorithms, stack expression conversion, sparse matrices, Fibonacci / Radix / Shell / Bucket sort, and linked-list variants (apart from the hash-table chains). Using a heap as a priority queue is not Heap Sort.</p>
        </section>
        <section className="card card-body doc">
          <h3 style={{ marginTop: 0 }}>Limitations</h3>
          <ul>
            <li>Educational simulation; the compatibility table is simplified and not clinical guidance.</li>
            <li>No authentication, real hospitals, maps or real patient data.</li>
            <li>Synthetic demo data only.</li>
          </ul>
        </section>
      </div>
    </>
  );
}
