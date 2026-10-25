import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  ArrowRight, FlaskConical, Grid3x3, Hash, Layers, ListOrdered, Loader2, Play, RotateCcw, Search, SortAsc,
} from "lucide-react";
import { api, BLOOD_GROUPS, fmtDate } from "../api.js";
import { ArrayStrip, HeapTree } from "../components/HeapViz.jsx";
import { ErrorBanner, GroupPill, LoadingBlock, PageHead, UrgencyBadge, useAsync } from "../components/ui.jsx";

const TABS = [
  { id: "heap", label: "Priority Heap", icon: ListOrdered },
  { id: "live", label: "Live Heaps (FEFO)", icon: Layers },
  { id: "sort", label: "Sorting", icon: SortAsc },
  { id: "search", label: "Searching", icon: Search },
  { id: "hash", label: "Hash Table", icon: Hash },
  { id: "compat", label: "Compatibility", icon: Grid3x3 },
];

export default function DsaLab() {
  const [params, setParams] = useSearchParams();
  const initial = TABS.some((t) => t.id === params.get("tab")) ? params.get("tab") : "heap";
  const [tab, setTabState] = useState(initial);
  const setTab = (id) => { setTabState(id); setParams({ tab: id }, { replace: true }); };
  return (
    <>
      <PageHead
        title="DSA Lab"
        subtitle="Every demo below calls the same classes and functions the real application uses. Nothing here is a separate fake implementation."
      />
      <div className="tabs" role="tablist">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} role="tab" aria-selected={tab === id} className={`tab ${tab === id ? "on" : ""}`} onClick={() => setTab(id)}>
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>
      {tab === "heap" && <HeapTab />}
      {tab === "live" && <LiveTab />}
      {tab === "sort" && <SortTab />}
      {tab === "search" && <SearchTab />}
      {tab === "hash" && <HashTab />}
      {tab === "compat" && <CompatTab />}
    </>
  );
}

const Stat = ({ value, label }) => (
  <div className="stat"><b style={String(value).length > 9 ? { fontSize: 14, lineHeight: 1.3 } : undefined}>{value}</b><span>{label}</span></div>
);
const heapNode = (e) => ({ title: e.label, sub: `U${e.urgency_level}·#${e.arrival_sequence}` });

/* ================= Priority heap (step-by-step) ================= */
const SAMPLE_OPS = [
  ["Clinic-A", 3], ["Surgery-B", 2], ["Routine-C", 3], ["Trauma-D", 1], ["Surgery-E", 2], ["Trauma-F", 1],
].map(([label, urgency_level]) => ({ op: "insert", label, urgency_level }));

function HeapTab() {
  const [ops, setOps] = useState(SAMPLE_OPS);
  const [label, setLabel] = useState("");
  const [urgency, setUrgency] = useState(2);
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!ops.length) { setData(null); return; }
    api.post("/dsa/heap-demo", { operations: ops }).then(setData).catch(setErr);
  }, [ops]);

  const last = data?.steps[data.steps.length - 1];
  const nodes = last ? last.array.map(heapNode) : [];

  return (
    <div className="grid grid-main">
      <div className="stack">
        <section className="card">
          <div className="card-head">
            <h3><ListOrdered size={17} /> Request priority heap</h3>
            <span className="muted small">min-heap on (urgency, arrival, id)</span>
          </div>
          <div className="card-body">
            <ErrorBanner error={err} />
            <HeapTree nodes={nodes} />
            <ArrayStrip nodes={nodes} />
            {last && (
              <div className="alert info" style={{ marginTop: 16 }}>
                <ArrowRight size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                  <b>Root (next to be processed): {last.root ? last.root.label : "—"}</b>
                  {last.root && <> — urgency {last.root.urgency_level} ({last.root.urgency_label}), arrival #{last.root.arrival_sequence}</>}
                </div>
              </div>
            )}
          </div>
        </section>

        {data && (
          <section className="card">
            <div className="card-head"><h3>Processing order from here</h3><span className="muted small">non-destructive copy of the heap</span></div>
            <div className="card-body">
              {data.processing_order.length === 0 ? <span className="muted">Heap is empty.</span> : (
                <div className="row">
                  {data.processing_order.map((e, i) => (
                    <span key={e.label} className="row" style={{ gap: 6 }}>
                      <span className="chip"><b>{i + 1}.</b> {e.label} <UrgencyBadge level={e.urgency_level} /></span>
                      {i < data.processing_order.length - 1 && <ArrowRight size={14} className="arrow" />}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}
      </div>

      <div className="stack">
        <section className="card">
          <div className="card-head"><h3>Operations</h3></div>
          <div className="card-body stack" style={{ gap: 12 }}>
            <div className="form-grid">
              <div className="field"><label>Label (optional)</label><input className="input" value={label} onChange={(e) => setLabel(e.target.value)} maxLength={14} placeholder="e.g. Clinic-A" /></div>
              <div className="field"><label>Urgency</label>
                <select className="select" value={urgency} onChange={(e) => setUrgency(Number(e.target.value))}>
                  <option value={1}>1 · Critical</option><option value={2}>2 · Surgery</option><option value={3}>3 · Routine</option>
                </select>
              </div>
            </div>
            <div className="row">
              <button className="btn primary" onClick={() => { setOps([...ops, { op: "insert", label: label.trim() || null, urgency_level: urgency }]); setLabel(""); }}>Insert</button>
              <button className="btn" onClick={() => setOps([...ops, { op: "extract" }])}>Extract root</button>
            </div>
            <div className="row">
              <button className="btn sm" onClick={() => setOps(SAMPLE_OPS)}>Load sample requests</button>
              <button className="btn sm" onClick={() => setOps([])}><RotateCcw size={14} /> Reset</button>
            </div>
            <p className="muted small">Arrival order is assigned automatically (1, 2, 3 …). Insert a Routine request first and a Critical one later, then extract: the Critical one still leaves first.</p>
          </div>
        </section>

        {last && (
          <section className="card">
            <div className="card-head"><h3>Last operation</h3></div>
            <div className="card-body stack" style={{ gap: 12 }}>
              <p>{last.description}</p>
              <div className="stat-row">
                <Stat value={last.comparisons} label="comparisons" />
                <Stat value={last.swaps} label="swaps" />
                <Stat value={data.size} label="items in heap" />
              </div>
              <div className="step-log">
                {data.steps.map((s, i) => (
                  <div key={i} className="log-line"><b>{i + 1}.</b><span>{s.description}</span></div>
                )).reverse()}
              </div>
              <p className="muted small">peek O(1) · insert O(log n) · extract O(log n)</p>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

/* ================= Live structures ================= */
function LiveTab() {
  const { data, loading, error, reload } = useAsync(() => api.get("/dsa/live"));
  const [picked, setGroup] = useState(null);
  if (error) return <ErrorBanner error={error} onRetry={reload} />;
  if (loading || !data) return <div className="card"><LoadingBlock /></div>;

  const group = picked || BLOOD_GROUPS.find((g) => data.fefo[g].length > 0) || "A+";
  const fefoNodes = (g) => data.fefo[g].map((b) => ({ title: b.label.replace("BAG-", "#"), sub: b.expiry_date.slice(5) }));
  const requestNodes = data.request_heap.map(heapNode);

  return (
    <div className="stack">
      <div className="alert info"><FlaskConical size={18} style={{ flexShrink: 0 }} /><span>These are the <b>real in-memory structures</b> of the running server (rebuilt from the database at start-up). Process a request, then press Refresh to watch them change.</span></div>
      <div className="row"><button className="btn" onClick={reload}><RotateCcw size={15} /> Refresh</button></div>

      <section className="card">
        <div className="card-head"><h3><ListOrdered size={17} /> Request heap ({requestNodes.length} waiting)</h3></div>
        <div className="card-body">
          <HeapTree nodes={requestNodes} />
          <ArrayStrip nodes={requestNodes} />
          <p className="muted small" style={{ marginTop: 10 }}>Each node shows request ID and U&lt;urgency&gt;·#&lt;arrival&gt;. Heap order is not sorted order: only the root is guaranteed to be the best.</p>
        </div>
      </section>

      <section className="card">
        <div className="card-head"><h3><Layers size={17} /> FEFO min-heaps, one per blood group</h3><span className="muted small">node = bag number, expiry month-day</span></div>
        <div className="card-body">
          <div className="row" style={{ marginBottom: 12 }} role="tablist" aria-label="Blood group">
            {BLOOD_GROUPS.map((g) => (
              <button key={g} className={`tab ${group === g ? "on" : ""}`} style={{ padding: "6px 10px" }} onClick={() => setGroup(g)} aria-selected={group === g}>
                {g} <span className="badge slate">{data.fefo[g].length}</span>
              </button>
            ))}
          </div>
          <HeapTree nodes={fefoNodes(group)} />
          <ArrayStrip nodes={fefoNodes(group)} />
        </div>
      </section>

      <section className="card">
        <div className="card-head"><h3>Next bag to expire in each group</h3><span className="muted small">the root of each heap, found in O(1)</span></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Group</th><th>Bags in heap</th><th>Root (earliest expiry)</th><th>Expires</th></tr></thead>
            <tbody>
              {BLOOD_GROUPS.map((g) => {
                const root = data.fefo[g][0];
                return (
                  <tr key={g}>
                    <td><GroupPill group={g} /></td><td>{data.fefo[g].length}</td>
                    <td className="mono bold">{root ? root.label : "—"}</td>
                    <td>{root ? fmtDate(root.expiry_date) : <span className="muted">empty</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid grid-2">
        {[["bag_index", "Bag-ID hash index"], ["request_index", "Request-ID hash index"]].map(([k, title]) => (
          <section key={k} className="card">
            <div className="card-head"><h3><Hash size={17} /> {title}</h3></div>
            <div className="card-body stat-row">
              <Stat value={data[k].entries} label="entries" />
              <Stat value={data[k].capacity} label="buckets" />
              <Stat value={data[k].load_factor} label="load factor" />
              <Stat value={data[k].collisions} label="collisions" />
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

/* ================= Sorting ================= */
function SortTab() {
  const [p, setP] = useState({ source: "inventory", sort_by: "expiry_date", order: "asc", algorithm: "merge" });
  const [sampleText, setSampleText] = useState("38, 27, 43, 3, 9, 82, 10, 27, 3, 55");
  const [results, setResults] = useState({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const key = JSON.stringify([p.source, p.sort_by, p.order, sampleText]);
  useEffect(() => { setResults({}); setErr(null); }, [key]);

  const body = (algorithm) => {
    const b = { ...p, algorithm };
    if (p.source === "sample") {
      const nums = sampleText.split(/[\s,]+/).filter(Boolean).map(Number);
      if (!nums.length || nums.some((n) => !Number.isInteger(n))) throw new Error("Enter whole numbers separated by commas (max 200).");
      b.sample = nums;
    }
    return b;
  };

  const run = async (algs) => {
    setBusy(true);
    setErr(null);
    try {
      const out = {};
      for (const a of algs) out[a] = await api.post("/dsa/sort-demo", body(a));
      setResults((r) => ({ ...r, ...out }));
      if (algs.length === 1) setP((q) => ({ ...q, algorithm: algs[0] }));
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const shown = results[p.algorithm] || results.merge || results.quick;
  const isInv = p.source === "inventory";
  const row = (x) => isInv
    ? <><td className="mono bold">{x.bag_id}</td><td><GroupPill group={x.blood_group} /></td><td>{x.expiry_date}</td><td>{x.collection_date}</td></>
    : <td className="mono bold">{String(x)}</td>;
  const head = isInv ? <tr><th>Bag</th><th>Group</th><th>Expiry</th><th>Collected</th></tr> : <tr><th>Value</th></tr>;

  return (
    <div className="stack">
      <section className="card card-body stack" style={{ gap: 14 }}>
        <div className="row">
          <div className="seg" role="group" aria-label="Data source">
            <button className={isInv ? "on" : ""} onClick={() => setP({ ...p, source: "inventory" })}>Live inventory</button>
            <button className={!isInv ? "on" : ""} onClick={() => setP({ ...p, source: "sample" })}>Sample numbers</button>
          </div>
          {isInv && (
            <select className="select" style={{ width: "auto" }} value={p.sort_by} onChange={(e) => setP({ ...p, sort_by: e.target.value })} aria-label="Sort key">
              <option value="expiry_date">expiry date</option><option value="collection_date">collection date</option>
              <option value="blood_group">blood group</option><option value="bag_id">bag ID</option>
            </select>
          )}
          <div className="seg" role="group" aria-label="Order">
            <button className={p.order === "asc" ? "on" : ""} onClick={() => setP({ ...p, order: "asc" })}>Ascending</button>
            <button className={p.order === "desc" ? "on" : ""} onClick={() => setP({ ...p, order: "desc" })}>Descending</button>
          </div>
        </div>
        {!isInv && <input className="input" value={sampleText} onChange={(e) => setSampleText(e.target.value)} aria-label="Sample numbers" />}
        <div className="row">
          <button className="btn primary" disabled={busy} onClick={() => run(["merge"])}>{busy ? <Loader2 size={16} className="spin" /> : <Play size={16} />} Run Merge Sort</button>
          <button className="btn primary" disabled={busy} onClick={() => run(["quick"])}><Play size={16} /> Run Quick Sort</button>
          <button className="btn" disabled={busy} onClick={() => run(["merge", "quick"])}>Compare both</button>
        </div>
        {err && <div className="alert bad" role="alert">{err}</div>}
      </section>

      {shown && (
        <>
          <section className="card">
            <div className="card-head">
              <h3>{shown.name} on {shown.n} item(s)</h3>
              <div className="row"><span className="badge slate">{shown.stable ? "stable" : "not stable"}</span><span className="badge slate">{shown.time}</span></div>
            </div>
            <div className="card-body stack" style={{ gap: 14 }}>
              <div className="stat-row">
                <Stat value={shown.comparisons} label="comparisons" />
                <Stat value={shown.data_moves} label={shown.moves_label} />
                <Stat value={shown.space} label="extra space" />
              </div>
              <div className="compare">
                <div><div className="step-title" style={{ marginBottom: 6 }}>Before (database order)</div>
                  <div className="mini-table"><table><thead>{head}</thead><tbody>{shown.before.map((x, i) => <tr key={i}>{row(x)}</tr>)}</tbody></table></div></div>
                <div><div className="step-title" style={{ marginBottom: 6 }}>After ({p.order === "asc" ? "ascending" : "descending"})</div>
                  <div className="mini-table"><table><thead>{head}</thead><tbody>{shown.after.map((x, i) => <tr key={i}>{row(x)}</tr>)}</tbody></table></div></div>
              </div>
              {shown.truncated && <p className="muted small">Only the first 200 bags are used for the demo.</p>}
            </div>
          </section>

          {results.merge && results.quick && (
            <section className="card">
              <div className="card-head"><h3>Merge Sort vs Quick Sort on the same data</h3></div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Algorithm</th><th>Comparisons</th><th>Moves</th><th>Time complexity</th><th>Extra space</th><th>Stable</th></tr></thead>
                  <tbody>
                    {["merge", "quick"].map((a) => (
                      <tr key={a}>
                        <td className="bold">{results[a].name}</td><td>{results[a].comparisons}</td>
                        <td>{results[a].data_moves} <span className="muted small">{results[a].moves_label}</span></td>
                        <td>{results[a].time}</td><td>{results[a].space}</td><td>{results[a].stable ? "Yes" : "No"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="table-foot">Operation counts for one run on this data are a teaching aid, not a benchmark. The Big-O columns describe general behaviour.</div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

/* ================= Searching ================= */
function SearchTab() {
  const [id, setId] = useState("BAG-1010");
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const { data: inv } = useAsync(() => api.get("/inventory", { sort_by: "bag_id" }));

  const run = async (e) => {
    e?.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const out = [];
      for (const method of ["linear", "binary", "hash"]) out.push(await api.post("/dsa/search-demo", { method, bag_id: id }));
      setRows(out);
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setBusy(false);
    }
  };
  const max = rows ? Math.max(...rows.map((r) => r.total_comparisons), 1) : 1;
  const names = { linear: "Linear Search", binary: "Binary Search", hash: "Hash Table" };

  return (
    <div className="stack">
      <section className="card card-body stack" style={{ gap: 14 }}>
        <form className="row" onSubmit={run}>
          <input className="input" style={{ maxWidth: 240 }} value={id} onChange={(e) => setId(e.target.value)} placeholder="Bag ID" aria-label="Bag ID" />
          <button className="btn primary" disabled={busy || !id.trim()}>{busy ? <Loader2 size={16} className="spin" /> : <Play size={16} />} Run all three methods</button>
        </form>
        {inv && (
          <div className="chips" style={{ marginTop: 0 }}>
            <span className="muted small" style={{ alignSelf: "center" }}>Try:</span>
            {inv.items.slice(0, 16).filter((_, i) => i % 3 === 0).map((b) => <button key={b.bag_id} className="chip mono" onClick={() => setId(b.bag_id)} style={{ cursor: "pointer" }}>{b.bag_id}</button>)}
            <button className="chip mono" style={{ cursor: "pointer" }} onClick={() => setId("BAG-9999")}>BAG-9999 (missing)</button>
          </div>
        )}
        {err && <div className="alert bad">{err}</div>}
      </section>

      {rows && (
        <section className="card">
          <div className="card-head"><h3>Same question, three algorithms</h3><span className="muted small">searching {rows[0].n} bags for {rows[0].target}</span></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Method</th><th>Result</th><th>Search steps</th><th>Sort needed first</th><th style={{ minWidth: 160 }}>Total work</th><th>Complexity</th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.method}>
                    <td className="bold">{names[r.method]}</td>
                    <td>{r.found ? <span className="badge green">Found</span> : <span className="badge rose">Not found</span>}</td>
                    <td>{r.comparisons}</td>
                    <td>{r.sort_comparisons ? `${r.sort_comparisons} comparisons` : "none"}</td>
                    <td><b>{r.total_comparisons}</b><div className="bar"><span style={{ width: `${(r.total_comparisons / max) * 100}%` }} /></div></td>
                    <td className="mono small">{r.complexity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card-body stack" style={{ gap: 8 }}>
            {rows.map((r) => <p key={r.method} className="small muted"><b>{names[r.method]}:</b> {r.precondition}.</p>)}
            <div className="alert info"><Search size={16} style={{ flexShrink: 0 }} /><span>Binary search needs a list sorted by the <b>same key</b>. Running it on unsorted data (or on a heap's array) would give wrong answers, so the code refuses unsorted input. For a single lookup the sorting cost makes it slower than linear search; it pays off when the sorted list is reused many times.</span></div>
          </div>
        </section>
      )}
    </div>
  );
}

/* ================= Hash table ================= */
function HashTab() {
  const [keysText, setKeysText] = useState(Array.from({ length: 12 }, (_, i) => `BAG-${1001 + i}`).join(", "));
  const [capacity, setCapacity] = useState(7);
  const [lookup, setLookup] = useState("BAG-1005");
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => {
      const keys = keysText.split(/[\s,]+/).filter(Boolean);
      api.post("/dsa/hash-demo", { keys, capacity, lookup: lookup || null }).then((d) => { setData(d); setErr(null); }).catch((e) => setErr(e.message));
    }, 250);
    return () => clearTimeout(t);
  }, [keysText, capacity, lookup]);

  return (
    <div className="grid grid-main">
      <section className="card">
        <div className="card-head"><h3><Hash size={17} /> Buckets (separate chaining)</h3><span className="muted small">fixed size here so collisions are visible</span></div>
        <div className="card-body">
          {err && <div className="alert bad" style={{ marginBottom: 12 }}>{err}</div>}
          {data?.buckets.map((b) => (
            <div key={b.index} className="bucket">
              <div className="bucket-idx">{b.index}</div>
              {b.keys.length === 0 ? <span className="muted small">empty</span> : b.keys.map((k, i) => (
                <span key={k} className="row" style={{ gap: 6 }}>
                  <span className="node" style={data.lookup?.found && data.lookup.key === k ? { background: "var(--primary)", color: "#fff" } : undefined}>{k}</span>
                  {i < b.keys.length - 1 && <ArrowRight size={13} className="arrow" />}
                </span>
              ))}
              {b.keys.length > 1 && <span className="badge amber">collision chain: {b.keys.length}</span>}
            </div>
          ))}
          <p className="muted small" style={{ marginTop: 12 }}>Index = hash(key) mod {capacity}. Two keys with the same index are <i>synonyms</i>; the later one is linked in front of the earlier one in that bucket's chain.</p>
        </div>
      </section>

      <div className="stack">
        <section className="card card-body stack" style={{ gap: 12 }}>
          <div className="field"><label>Keys to insert (comma separated)</label><textarea className="textarea" rows={3} value={keysText} onChange={(e) => setKeysText(e.target.value)} /></div>
          <div className="field"><label>Number of buckets: {capacity}</label><input type="range" min="3" max="31" value={capacity} onChange={(e) => setCapacity(Number(e.target.value))} /></div>
          <div className="field"><label>Look up a key</label><input className="input" value={lookup} onChange={(e) => setLookup(e.target.value)} /></div>
          {data && (
            <>
              <div className="stat-row">
                <Stat value={data.entries} label="entries" /><Stat value={data.collisions} label="collisions" /><Stat value={data.load_factor} label="load factor" />
              </div>
              {data.lookup && (
                <div className={`alert ${data.lookup.found ? "good" : "warn"}`}>
                  {data.lookup.found ? "Found" : "Not found"} in bucket {data.lookup.bucket}; {data.lookup.chain_nodes_visited} chain node(s) visited.
                </div>
              )}
            </>
          )}
        </section>
        {data && (
          <section className="card">
            <div className="card-head"><h3>Hash of each key</h3><span className="muted small">djb2</span></div>
            <div className="mini-table" style={{ border: 0, borderRadius: 0 }}>
              <table><thead><tr><th>Key</th><th>Hash code</th><th>Bucket</th></tr></thead>
                <tbody>{data.keys.map((k) => <tr key={k.key}><td className="mono bold">{k.key}</td><td className="mono">{k.hash_code}</td><td><b>{k.bucket}</b></td></tr>)}</tbody></table>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

/* ================= Compatibility matrix ================= */
function CompatTab() {
  const { data, loading, error, reload } = useAsync(() => api.get("/dsa/compatibility"));
  const [pick, setPick] = useState("AB+");
  if (error) return <ErrorBanner error={error} onRetry={reload} />;
  if (loading || !data) return <div className="card"><LoadingBlock rows={4} /></div>;
  const row = data.rows.find((r) => r.recipient === pick);

  return (
    <div className="grid grid-main">
      <section className="card">
        <div className="card-head">
          <h3><Grid3x3 size={17} /> Compatibility matrix (8×8 array)</h3>
          <span className="badge amber">{data.mode === "exact" ? "Exact-match mode" : "Simplified educational table"}</span>
        </div>
        <div className="card-body table-wrap">
          <table className="matrix">
            <thead>
              <tr><th style={{ textAlign: "right", fontSize: 11 }}>requested ↓ / donor stock →</th>{data.groups.map((g) => <th key={g}><GroupPill group={g} dim /></th>)}</tr>
            </thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.recipient}>
                  <th style={{ textAlign: "right" }}><button className="btn sm" onClick={() => setPick(r.recipient)} style={pick === r.recipient ? { borderColor: "var(--primary)" } : undefined}><GroupPill group={r.recipient} on={pick === r.recipient} /></button></th>
                  {r.cells.map((ok, i) => <td key={i}><div className={`mcell ${ok ? "on" : ""}`} aria-label={ok ? "eligible" : "not eligible"}>{ok ? "✓" : "–"}</div></td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <div className="stack">
        <section className="card card-body stack" style={{ gap: 10 }}>
          <h3>A request for <GroupPill group={pick} on /> may use stock of:</h3>
          <div className="chips">{data.groups.filter((g, i) => row.cells[i]).map((g) => <GroupPill key={g} group={g} />)}</div>
          <p className="muted small">Row = requested group, column = donor stock group. Code: <code>get_compatible_donor_groups("{pick}")</code> reads that row of the 2-D array.</p>
        </section>
        <div className="alert warn">Simplified teaching table for a data-structures project. It is not clinical guidance and must never be used for real transfusion decisions.</div>
      </div>
    </div>
  );
}
