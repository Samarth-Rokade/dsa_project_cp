# Smart Emergency Blood Allocation & Dispatch Engine

> **Prioritize urgent requests. Allocate compatible stock. Reduce expiry waste.**

A full-stack capstone project for a second-year **Data Structures & Algorithms** course. Hospitals send blood requests with different urgency levels; the blood bank holds bags with different groups and expiry dates. The engine decides **which request to serve next**, **which stored bags are allowed**, and **which bags to use first**, using data structures and algorithms written by hand (no built-in sort / priority-queue calls in the assessed logic).

> ⚠️ **Educational simulation only.** The blood-group compatibility table is a simplified *teaching* table. The app uses synthetic data, is not clinical decision support, and must never be used for real transfusion decisions.

---

## Table of contents

1. [Tech stack](#1-tech-stack)
2. [Features](#2-features)
3. [Quick start](#3-quick-start)
4. [Project structure](#4-project-structure)
5. [Architecture](#5-architecture)
6. [Data structures & algorithms (the core of the project)](#6-data-structures--algorithms)
7. [How "Process Next Request" works](#7-how-process-next-request-works)
8. [Compatibility table](#8-compatibility-table)
9. [Demo walkthrough](#9-demo-walkthrough-6-clicks)
10. [API reference](#10-api-reference)
11. [Database](#11-database-and-switching-to-another-one)
12. [Testing](#12-testing)
13. [Design decisions & assumptions](#13-design-decisions--assumptions)
14. [Viva cheat-sheet](#14-viva-cheat-sheet)
15. [Limitations & future work](#15-limitations--future-work)

---

## 1. Tech stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | **React 18** + **Vite** | Fast dev server, simple component model |
| Routing / icons | React Router, Lucide icons | Page navigation, consistent icon set |
| Styling | Hand-written CSS (design tokens, responsive) | No extra build tooling to explain |
| Backend | **FastAPI** (Python 3.10+) | Very little boilerplate, automatic validation, free API docs at `/docs` |
| Validation | **Pydantic v2** | Rejects bad blood groups, urgency, quantities, dates |
| ORM | **SQLAlchemy 2.0** | Same code runs on SQLite, PostgreSQL, MySQL… |
| Database | **SQLite** (development) | Zero setup, one file (`backend/bloodbank.db`) |
| Tests | **pytest** + FastAPI `TestClient` | 82 automated tests |

The assessed DSA code (`backend/app/dsa/`) uses **only the Python standard library** – no third-party algorithm helpers.

---

## 2. Features

| Page | What you can do |
|---|---|
| **Dashboard** | Live KPIs (available units, registered bags, pending/critical requests, expiring-soon, expired), stock per blood group, expiry warnings, live priority queue, recent dispatches. Every number comes from the database. |
| **Blood Inventory** | Add / edit / discard bags, search by bag ID, filter by group and status, sort by expiry / collection date / group / bag ID using **our Merge Sort or Quick Sort** (switchable), expired stock visibly separated, exact-bag lookup comparing Linear vs Binary vs Hash search. |
| **Hospital Requests** | Create requests, see priority position and arrival order, filter by status / urgency, search, cancel (with confirmation), and **Process Next Request** with a step-by-step explanation of why that request and those bags were chosen. |
| **Dispatch History** | Append-only log (no edit/delete). Sorted by time with Merge Sort. Expand a row to see the decision explanation and the exact bags. |
| **DSA Lab** | Interactive demos of the *real* implementations: step-by-step priority heap (tree + array), live heaps from the running server, Merge vs Quick Sort with operation counts, three search methods side by side, hash-table buckets & collisions, the 8×8 compatibility matrix. |
| **About / DSA Notes** | Why each structure fits, where it is used, how it works, how it is tested, complexity table. |
| **Settings** | Expiry warning window, compatibility mode (educational table / exact match only), **Reset demo data** (with confirmation). |

UI quality points: loading skeletons, empty states, error banners with retry, toast notifications, inline form validation (client **and** server errors), confirmation dialogs for destructive actions, status/urgency shown with **icon + text** (never colour alone), responsive layout with mobile menu, scrolling tables.

---

## 3. Quick start

**Requirements:** Python 3.10+ and Node.js 18+.

### Windows (double-click or run in a terminal)
```bat
setup.bat            :: one-time: creates the venv, installs Python + npm packages
run-backend.bat      :: terminal 1 -> http://localhost:8000  (API docs: /docs)
run-frontend.bat     :: terminal 2 -> http://localhost:5173  (open this one)
```

### Manual commands
```bash
# --- backend ---
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload     # creates bloodbank.db and seeds demo data on first start

# --- frontend (new terminal) ---
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The first start seeds synthetic demo data automatically. Use *Settings → Reset demo data* to start the walkthrough again.

### Run the tests
```bash
cd backend
pytest -q          # 82 tests
```

---

## 4. Project structure

```text
dsa_project_cp/
├── README.md
├── setup.bat · run-backend.bat · run-frontend.bat
├── backend/
│   ├── requirements.txt · pytest.ini
│   ├── app/
│   │   ├── main.py              FastAPI app, start-up (create tables, seed, rebuild structures)
│   │   ├── config.py            DATABASE_URL (the only DB setting)
│   │   ├── database.py          SQLAlchemy engine / session
│   │   ├── models.py            ORM tables
│   │   ├── schemas.py           Pydantic request validation
│   │   ├── errors.py            centralised error handling (one JSON shape)
│   │   ├── serializers.py       ORM row -> JSON dict
│   │   ├── seed.py              synthetic demo data + reset
│   │   ├── dsa/                 ★ generic, hand-written data structures & algorithms
│   │   │   ├── binary_heap.py       array-based binary heap
│   │   │   ├── fefo_inventory.py    one min-heap per blood group
│   │   │   ├── merge_sort.py        stable, divide & conquer
│   │   │   ├── quick_sort.py        median-of-three, in place
│   │   │   ├── searching.py         linear + binary search
│   │   │   └── hash_table.py        separate chaining
│   │   ├── domain/              application rules (no HTTP, no UI)
│   │   │   ├── compatibility.py     8×8 matrix + lookup
│   │   │   ├── priority.py          THE request comparator
│   │   │   ├── allocation_service.py  Process-Next algorithm (transactional)
│   │   │   ├── state.py             in-memory structures rebuilt from the DB
│   │   │   ├── sorting.py · settings.py
│   │   └── routes/              HTTP only: inventory, requests, dispatches, analytics, dsa_lab, admin
│   └── tests/                   pytest suite
└── frontend/
    ├── package.json · vite.config.js (proxies /api -> :8000)
    └── src/
        ├── App.jsx · main.jsx · api.js · index.css
        ├── components/          ui.jsx (badges, modal, toasts…), HeapViz.jsx, ProcessResult.jsx
        └── pages/               Dashboard, Inventory, Requests, Dispatches, DsaLab, About, Settings
```

Rule that keeps the project explainable: **`dsa/` knows nothing about HTTP or the database**; **`domain/`** applies the business rules; **`routes/`** only translate HTTP. No heap code lives inside a route or a React component.

---

## 5. Architecture

```text
  React (browser)  ──HTTP/JSON──▶  FastAPI routes  ──▶  domain services  ──▶  dsa/ (heaps, sorts, search, hash)
                                        │                     │
                                        ▼                     ▼
                                  Pydantic validation    SQLAlchemy ──▶ SQLite (source of truth)
```

**Two copies of the data, one source of truth.**
The **database is the permanent record**. While the server runs it also keeps fast **in-memory structures** built from it:

| In-memory structure | Built from | Used for |
|---|---|---|
| Request heap | requests with status `pending` / `partially_fulfilled` | choosing the next request |
| 8 FEFO min-heaps | bags with status `available` | choosing the earliest-expiring bag |
| Bag-ID hash table | all bags | O(1) lookup + duplicate-ID check |
| Request-ID hash table | all requests | O(1) lookup |

They are **rebuilt from the database on every server start** (`InMemoryState.rebuild`), so a restart loses nothing. New bags/requests are inserted incrementally (`O(log n)`); edits and cancellations simply rebuild from the database (`O(n)` heapify).

**Transaction safety.** `process_next_request` changes bags, the request and the dispatch log in **one database transaction**. If anything fails it rolls back and rebuilds the in-memory structures, so a failure can never be reported as a success. A lock ensures only one allocation runs at a time.

### Database schema

```text
blood_bags          id, bag_id (unique), blood_group, collection_date, expiry_date, volume_ml,
                    location, status, created_at, updated_at      CHECK expiry_date > collection_date
hospital_requests   id, request_id (unique), hospital_name, required_blood_group, units_needed,
                    units_allocated, urgency_level (1-3), arrival_sequence (unique), status, notes, ...
dispatches          id, request_pk → hospital_requests, processed_at, units_allocated, units_remaining,
                    result, groups_considered, decision_summary
dispatch_items      id, dispatch_id → dispatches, blood_bag_pk → blood_bags, donor_blood_group,
                    expiry_date_at_dispatch
app_settings        key, value                                   (expiry warning days, compatibility mode)
```

Bag status: `available · reserved · dispatched · expired · discarded`.
Request status: `pending · partially_fulfilled · fulfilled · cancelled`.

---

## 6. Data structures & algorithms

For every structure: **Why it fits · Where it is used · How it works · How it is verified.**

### 6.1 Binary Heap — emergency request queue  *(MUST-HAVE)*
- **Why:** the next request must always be the most urgent one, and new requests keep arriving. A heap gives the best item instantly and stays ordered cheaply.
- **Where:** `dsa/binary_heap.py`, comparator in `domain/priority.py`, used by `allocation_service.py` (`state.request_heap`).
- **How:** a *complete binary tree stored in an array*.
  `parent(i) = (i-1)//2`, `left(i) = 2i+1`, `right(i) = 2i+2`.
  **Invariant:** no child comes before its parent → the best item is at index 0.
  - `insert`: append at the end, **sift up** while it beats its parent.
  - `extract`: take the root, move the last item to the root, **sift down** while a child beats it.
  - `build_heap`: Floyd's bottom-up heapify, sift down from the last parent to the root.
- **Priority order (one comparator):** urgency `1 → 2 → 3`, then **earlier arrival sequence**, then request ID. Because *1 is most urgent*, it is a **min-heap** on the tuple `(urgency, arrival, id)`.
- **Verified:** `tests/test_binary_heap.py` — critical beats an earlier routine request, ties by arrival, empty-heap behaviour (`peek`/`extract` return `None`), 500 random operations keep the invariant.

### 6.2 Per-blood-group Min-Heaps — FEFO inventory  *(MUST-HAVE)*
- **Why:** to reduce expiry waste, the bag that expires first must be used first (First-Expired-First-Out).
- **Where:** `dsa/fefo_inventory.py` (`FefoInventory`), used in `allocation_service.py`.
- **How:** the **same `BinaryHeap` class**, a different comparator `(expiry_date, bag_id)`, one heap per blood group. The root of each heap is the next bag of that group to expire. For a request we look at the roots of all *compatible* groups and take the smallest (a k-way pick, k ≤ 8). Expired roots are removed first — only the root needs checking, because no child expires earlier than its parent.
- **Expiry rule:** a bag is usable **through** its expiry date; it is expired when `expiry_date < today`.
- **Verified:** `tests/test_fefo_compatibility.py` — earliest expiry first, equal expiry → smaller bag ID, expired never returned, unavailable bags never enter the heaps, rebuild-from-database after restart.

### 6.3 Compatibility matrix — 2-D array lookup  *(MUST-HAVE)*
- **Why:** compatibility must come from a table, never from string tricks.
- **Where:** `domain/compatibility.py`; used before any allocation; displayed in DSA Lab → Compatibility.
- **How:** an **8×8 array**, row = requested (recipient) group, column = donor stock group. `get_compatible_donor_groups(group)` reads one row. A second mode (`exact`) allows only the identical group.
- **Verified:** all 8 groups, direction (request → donors), ineligible groups excluded, exact-match mode, unknown group rejected.

### 6.4 Merge Sort & Quick Sort  *(MUST-HAVE, two sorts)*
| | Merge Sort (`dsa/merge_sort.py`) | Quick Sort (`dsa/quick_sort.py`) |
|---|---|---|
| Idea | split in halves, sort each (recursion), **merge** | pick pivot, **partition**, sort both sides |
| Time | **O(n log n)** always | average O(n log n), **worst O(n²)** |
| Extra space | O(n) | O(log n) stack (in place) |
| Stable | **Yes** | No |
| Pivot | – | **median-of-three** (avoids the sorted-input worst case); recurse into the smaller side so the stack stays O(log n) |

- **Where:** every sortable list — inventory (switch algorithm in the UI), request list, dispatch history, dashboard expiry list, DSA Lab. `domain/sorting.py` defines the sort keys; every key ends with the bag ID so ties are deterministic.
- **Verified:** `tests/test_sorting_searching.py` — ascending/descending, empty/single/sorted/reversed input, duplicates, stability, 50 random lists compared with Python's `sorted()` (used **only inside the test assertions**).

### 6.5 Linear Search & Binary Search  *(MUST-HAVE, two searches)*
- **Linear search** — works on any list, `O(n)`.
- **Binary search** — `O(log n)` but **only on a list sorted by the exact search key**. `binary_search` checks this precondition and raises `UnsortedInputError` instead of returning a wrong answer. It is **never** run on a heap's array (a heap is only partly ordered).
- **Where:** `dsa/searching.py`; Inventory → *Exact bag lookup* and DSA Lab → Searching. For binary search the app sorts by bag ID first and **reports the sorting cost too**, so the true end-to-end cost is not hidden.
- **Verified:** found / not found / empty / unsorted-input-rejected / key function.

### 6.6 Hash Table with separate chaining  *(recommended addition)*
- **Why:** exact lookups by bag ID / request ID, and instant duplicate-ID detection.
- **Where:** `dsa/hash_table.py`; `domain/state.py` (`bag_index`, `request_index`); duplicate check in *Add bag*; lookup in `GET /api/inventory/{bag_id}`.
- **How:** array of buckets; each bucket is a chain of linked nodes. Hash function **djb2** (`h = h*33 + ord(c)`), `index = h % capacity`. A **collision** (two keys, same bucket) simply extends the chain. When the load factor exceeds 0.75 the table doubles and rehashes. It is an *in-memory index*; the database remains the permanent store (the index stores bag ID → database primary key).
- **Complexity:** average `O(1)`, worst case `O(n)` (all keys in one chain).
- **Verified:** put/get/update/delete, forced collisions, resize keeps every entry, deterministic hash.

### 6.7 Complexity table

| Operation | Data structure / algorithm | Expected complexity |
|---|---|---:|
| Peek next request | Binary heap | `O(1)` |
| Insert request | Binary heap | `O(log n)` |
| Remove highest-priority request | Binary heap | `O(log n)` |
| Build heap from n items (start-up, cancel) | Bottom-up heapify | `O(n)` |
| Peek earliest expiry in one group | Min-heap | `O(1)` |
| Insert / remove one bag | Min-heap | `O(log n)` |
| Linear search | Array | `O(n)` |
| Binary search (after sorting) | Sorted array | `O(log n)` |
| Merge Sort | Array | `O(n log n)` time, `O(n)` extra space |
| Quick Sort | Array | average `O(n log n)`, worst `O(n²)` |
| Hash-table lookup | Chained hash table | average `O(1)`, worst `O(n)` |
| Database queries | SQLite / SQLAlchemy | depends on indexes — not claimed as a DSA bound |

> The whole allocation is **not** `O(log n)`: it checks several compatible groups and may allocate many bags, so its cost depends on the groups and bags actually processed (≈ `O(k + m log n)` for `m` allocated bags across `k ≤ 8` groups).

### 6.8 Syllabus mapping — honest coverage

| Syllabus topic | Status |
|---|---|
| Arrays, 2-D arrays | ✅ inventory snapshots, sorted copies, 8×8 compatibility matrix |
| Searching: linear, binary | ✅ implemented + tested |
| Sorting: merge, quick | ✅ implemented + tested; comparison in DSA Lab |
| Complexity analysis | ✅ tables above, operation counters in the UI |
| Recursion | ✅ merge sort and quick sort are recursive (base case, call stack) |
| Trees (binary tree in an array) | ✅ only as the **binary heap** (complete binary tree) |
| Hashing: hash function, collision, chaining | ✅ implemented + tested |
| Linked list | ➖ only the **chain nodes inside the hash table**; no separate list feature |
| Stack / queue | ➖ not used (the request queue is a *priority* queue = heap) |
| **Deliberately NOT claimed:** Heap Sort (using a heap ≠ Heap Sort), BST / threaded trees, BFS/DFS & other graph algorithms, expression conversion, sparse matrices, Fibonacci / Radix / Shell / Bucket sort, open addressing | ❌ out of scope — adding them would be fake coverage |

---

## 7. How "Process Next Request" works

One click processes **exactly one** request:

1. **Purge expired stock.** Expired roots are removed from the FEFO heaps and marked `expired` in the database. Expired bags are never allocated.
2. **Pick the request.** `extract()` the root of the request heap (urgency, then arrival).
3. **Look up compatible donor groups** in the compatibility matrix (or the exact group in exact mode).
4. **No compatible stock?** The request **stays pending** and the next request in priority order is tried, so one blocked critical request can never starve everyone else. Skipped requests are named in the explanation. If *no* waiting request can be served, one `no_stock` dispatch is logged with the shortage.
5. **FEFO allocation.** Repeatedly take the earliest-expiring bag among the compatible groups until the units are covered or stock runs out.
6. **Save in one transaction:** bags → `dispatched`, request `units_allocated` / status, a dispatch record and one dispatch item per bag.
7. **Requeue policy.** A partially fulfilled request is **re-inserted into the heap with its remaining units and its original arrival sequence** (it does not lose its place). It is *not* processed again automatically — the UI only ever processes one request per click.

Outcomes: `fulfilled`, `partially_fulfilled` (≥ 1 unit allocated, shortage shown), `no_stock` (request stays `pending`, shortage shown).

The result panel explains each step in plain language (why this request, which groups, which bags and why, what is still missing).

---

## 8. Compatibility table

**Simplified educational red-cell table.** Row = *requested* group, columns = *donor stock groups allowed*. Direction matters: it is **request → donors**.

| Requested | Donor stock allowed |
|---|---|
| O− | O− |
| O+ | O+, O− |
| A− | A−, O− |
| A+ | A+, A−, O+, O− |
| B− | B−, O− |
| B+ | B+, B−, O+, O− |
| AB− | AB−, A−, B−, O− |
| AB+ | all eight groups |

Consequences you can see in the tests: O− stock is eligible for every request; AB+ stock is eligible only for AB+ requests. **Not clinically validated.** Switch to *Exact match only* in Settings for the strictest behaviour.

---

## 9. Demo walkthrough (6 clicks)

The seed data (16 bags, 7 requests; dates are relative to today) is designed so that pressing **Process next request** six times on the *Hospital Requests* page shows every outcome:

| Click | Request | Result | What it demonstrates |
|---|---|---|---|
| 1 | REQ-0003 Critical O−, 2 units | ✅ fulfilled | Critical goes before older routine requests; expired `BAG-1003` is purged first; FEFO uses the two O− bags |
| 2 | REQ-0007 Critical A+, 1 unit | ✅ fulfilled with an **O+** bag | compatible alternative: the O+ bag expires sooner than any A+ bag |
| 3 | REQ-0004 Surgery B+, 8 units | 🟡 partial 5/8 | FEFO across B+ and O+; shortage of 3 shown |
| 4 | REQ-0002 Routine A+, 3 units | ✅ fulfilled | `BAG-1008` & `BAG-1009` share an expiry date → tie-break by bag ID; REQ-0004 and REQ-0005 are skipped (no stock) and stay pending |
| 5 | REQ-0006 Routine AB+, 2 units | 🟡 partial 1/2 | only one AB+ bag remained |
| 6 | (nothing can be served) | 🔴 no stock | shortage reported, requests stay in the queue |

Then open **DSA Lab → Live Heaps** to see the heaps after those operations, and **Dispatch History** to read every explanation. *(Automated test `test_full_demo_walkthrough_on_seed_data` checks exactly this sequence.)*

---

## 10. API reference

Interactive docs: **http://localhost:8000/docs**. Errors always look like `{"error": {"message": "...", "fields": {"field": "msg"}}}`.

| Method & path | Purpose |
|---|---|
| `GET /api/inventory` | list; filters `blood_group, status, search`; sort `sort_by, order, algorithm=merge\|quick` |
| `GET /api/inventory/summary` | counts by group and status |
| `GET /api/inventory/{bag_id}` | one bag (hash-table index) |
| `POST /api/inventory` | add bag (validates group, dates, duplicate ID) |
| `PATCH /api/inventory/{bag_id}` | edit details / reserve / discard |
| `POST /api/inventory/sweep-expired` | purge expired bags from the heaps |
| `GET /api/requests` | list; filters `status, urgency, search`; sort `priority\|arrival\|units_needed` |
| `GET /api/requests/queue` | waiting requests in live heap order |
| `GET /api/requests/{request_id}` | one request |
| `POST /api/requests` | create request |
| `PATCH /api/requests/{request_id}/cancel` | cancel a waiting request |
| `POST /api/requests/process-next` | process **one** request, returns the explanation |
| `GET /api/dispatches` · `GET /api/dispatches/{id}` | history (read-only) |
| `GET /api/analytics/dashboard` | all dashboard numbers |
| `GET/PUT /api/settings` · `POST /api/admin/reset-demo` | settings, demo reset |
| `POST /api/dsa/heap-demo` · `/sort-demo` · `/search-demo` · `/hash-demo` · `GET /api/dsa/live` · `/compatibility` | DSA Lab (algorithm names and input sizes are validated; no code execution) |

---

## 11. Database and switching to another one

The database is chosen by **one environment variable**. Nothing else in the code mentions SQLite.

```bash
# default (development)
sqlite:///backend/bloodbank.db

# PostgreSQL later — install a driver (pip install "psycopg[binary]") and set:
set DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/bloodbank
```

Tables are created automatically at start-up (`Base.metadata.create_all`). For a production-style setup you would add **Alembic** migrations (not included, to keep the project small). The code uses only portable SQLAlchemy features (`Date`, `DateTime`, `CheckConstraint`, foreign keys).

---

## 12. Testing

```bash
cd backend
pytest -q
```

**82 tests**, all independent of the UI. DSA tests do not touch the database; service/API tests use a throw-away in-memory SQLite database.

| Area | Test file | Covers |
|---|---|---|
| Heap / priority | `test_binary_heap.py` | critical-before-routine, arrival tie-break, empty heap, random operations keep the invariant, build-heap, comparator direction |
| FEFO + compatibility | `test_fefo_compatibility.py` | earliest expiry, tie-break by bag ID, expired never allocated, new bag in the right heap, **restart rebuild**, all 8 groups, direction, exact mode |
| Sorting / searching / hash | `test_sorting_searching.py` | both sorts vs trusted result, stability, duplicates, linear / binary search, unsorted rejection, collisions, resize |
| Allocation workflow | `test_allocation_service.py` | fulfilled / partial / no-stock, cross-group alternative, expired & unavailable bags never used, requeue policy, no starvation, one request per call, each bag dispatched once, cancelled/fulfilled not reprocessed, **database failure ⇒ rollback & no false success** |
| API | `test_api.py` | validation errors (blood group, urgency, units, dates, duplicate ID), dashboard numbers change after actions, configurable expiry window, filters/sorting, the full 6-click walkthrough, reset, DSA Lab endpoints |

The frontend was also exercised end-to-end in a real browser (reset → process requests → forms with validation errors → every DSA Lab tab → mobile layout) with no console errors.

---

## 13. Design decisions & assumptions

- **Stack chosen for ease:** React + FastAPI + SQLAlchemy + SQLite (instead of the Node/TypeScript stack suggested in the original brief). The frontend uses plain JavaScript (JSX) and hand-written CSS to keep the code easy to read in a viva.
- **FEFO ignores group preference:** among all compatible groups the earliest expiry wins (even if that means using an O+ bag for an A+ request, as in click 2). This best serves the goal *reduce expiry waste*. A "prefer exact match first" rule would be a one-line change in `pop_earliest_among`.
- **Blocked requests are skipped, not stuck:** see §7 step 4 — this prevents starvation and is documented and tested.
- **Expiry is date-based:** usable through the expiry date. Expired bags still marked `available` are shown as *Expired* immediately and moved to `expired` on the next sweep / allocation.
- **Blood group cannot be edited** after registration (it would change which heap the bag lives in); discard and re-add instead.
- **Dispatch history is append-only:** there is deliberately no update/delete endpoint.
- **Single process, one lock:** appropriate for a course project; a multi-server deployment would need the allocation to lock in the database instead.
- **No authentication, real hospitals, maps or patient data.** Notes fields warn against entering identifying information.

---

## 14. Viva cheat-sheet

**Why a heap and not a sorted array for requests?**
Requests arrive continuously. A sorted array needs `O(n)` per insert; a heap needs `O(log n)` and gives the best item in `O(1)`. We only ever need the *next* item, not a fully sorted list.

**Is a heap sorted? Can I binary-search it?**
No. A heap only guarantees parent ≤ children, so only the root is known. Binary search needs a fully sorted array — we sort a copy by bag ID first (and report that cost) or use the hash table.

**Why per-group heaps for FEFO instead of one big heap?**
Each request only cares about a few compatible groups. With one heap per group we look at ≤ 8 roots instead of searching the whole stock.

**How do you break ties?**
Requests: urgency → arrival sequence → request ID. Bags: expiry date → bag ID. Always deterministic.

**Merge Sort vs Quick Sort?**
Merge Sort: guaranteed `O(n log n)`, stable, needs `O(n)` extra space. Quick Sort: average `O(n log n)` but worst `O(n²)`, in place, not stable. We use median-of-three pivots to avoid the sorted-input worst case.

**What is a collision and how is it handled?**
Two keys with the same bucket index. We use separate chaining: each bucket holds a linked chain, so both keys are stored. Load factor > 0.75 → the table doubles and rehashes.

**Why is the whole allocation not O(log n)?**
It may look at several groups and allocate many bags; the cost grows with the number of bags allocated.

**What happens if the server restarts or the database write fails?**
Restart: heaps and hash indexes are rebuilt from the database. Failure: the transaction is rolled back, the in-memory structures are rebuilt, and an error is returned — never a false success.

**What happens to a partially fulfilled request?**
It goes back into the heap with its remaining units and original arrival sequence, and waits for more stock.

**Is this medically valid?**
No. It is an educational simulation with a simplified compatibility table.

---

## 15. Limitations & future work

- Simplified, **non-clinical** compatibility table; synthetic data only.
- No authentication or multi-user concurrency control beyond one in-process lock.
- Migrations (Alembic), Docker, and a frontend test suite are not included.
- Possible extensions *(only if the course scope grows)*: multi-bank logistics with distance sorting, a circular-queue event buffer, a separate singly-linked-list lab exercise.
