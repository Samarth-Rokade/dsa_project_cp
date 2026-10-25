import { useEffect, useState } from "react";
import { Boxes, Loader2, Pencil, Plus, Search, SearchCheck, Trash2, Zap } from "lucide-react";
import { api, BLOOD_GROUPS, fmtDate } from "../api.js";
import {
  BagStatusBadge, ConfirmDialog, EmptyState, ErrorBanner, Field, GroupPill, LoadingBlock, Modal, PageHead,
  useAsync, useToast,
} from "../components/ui.jsx";

const todayPlus = (days) => {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
};

export default function Inventory() {
  const toast = useToast();
  const [f, setF] = useState({ search: "", blood_group: "", status: "", sort_by: "expiry_date", order: "asc", algorithm: "merge" });
  const [debounced, setDebounced] = useState(f.search);
  const [editing, setEditing] = useState(null);     // null | "new" | bag
  const [discarding, setDiscarding] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(f.search), 250);
    return () => clearTimeout(t);
  }, [f.search]);

  const { data, loading, error, reload } = useAsync(
    () => api.get("/inventory", { ...f, search: debounced }),
    [debounced, f.blood_group, f.status, f.sort_by, f.order, f.algorithm]
  );
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const discard = async () => {
    setBusy(true);
    try {
      await api.patch(`/inventory/${discarding.bag_id}`, { status: "discarded" });
      toast(`${discarding.bag_id} marked as discarded`);
      setDiscarding(null);
      reload();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const sweep = async () => {
    try {
      const r = await api.post("/inventory/sweep-expired");
      toast(r.count ? `${r.count} expired bag(s) removed from the FEFO heaps` : "No expired bags in the heaps");
      reload();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const items = data?.items || [];

  return (
    <>
      <PageHead title="Blood Inventory" subtitle="Every bag is stored in the database and loaded into a per-group FEFO heap. Lists are sorted with our own Merge Sort / Quick Sort.">
        <button className="btn" onClick={sweep}><Zap size={16} /> Sweep expired</button>
        <button className="btn primary" onClick={() => setEditing("new")}><Plus size={16} /> Add blood bag</button>
      </PageHead>

      <ErrorBanner error={error} onRetry={reload} />

      <div className="card">
        <div className="filters">
          <div className="search-wrap">
            <Search size={16} />
            <input className="input" placeholder="Search bag ID…" value={f.search} onChange={set("search")} aria-label="Search bag ID" />
          </div>
          <select className="select" value={f.blood_group} onChange={set("blood_group")} aria-label="Blood group">
            <option value="">All groups</option>
            {BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}
          </select>
          <select className="select" value={f.status} onChange={set("status")} aria-label="Status">
            <option value="">All statuses</option>
            {["available", "reserved", "dispatched", "expired", "discarded"].map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
          </select>
          <span className="spacer" />
          <select className="select" value={f.sort_by} onChange={set("sort_by")} aria-label="Sort by">
            <option value="expiry_date">Sort: expiry date</option>
            <option value="collection_date">Sort: collection date</option>
            <option value="blood_group">Sort: blood group</option>
            <option value="bag_id">Sort: bag ID</option>
          </select>
          <div className="seg" role="group" aria-label="Order">
            <button className={f.order === "asc" ? "on" : ""} onClick={() => setF({ ...f, order: "asc" })}>Asc</button>
            <button className={f.order === "desc" ? "on" : ""} onClick={() => setF({ ...f, order: "desc" })}>Desc</button>
          </div>
          <div className="seg" role="group" aria-label="Sorting algorithm">
            <button className={f.algorithm === "merge" ? "on" : ""} onClick={() => setF({ ...f, algorithm: "merge" })}>Merge Sort</button>
            <button className={f.algorithm === "quick" ? "on" : ""} onClick={() => setF({ ...f, algorithm: "quick" })}>Quick Sort</button>
          </div>
        </div>

        {loading && !data ? (
          <LoadingBlock />
        ) : items.length === 0 ? (
          <EmptyState icon={Boxes} title="No bags match" text="Change the filters or add a new blood bag." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Bag ID</th><th>Group</th><th>Status</th><th>Collected</th><th>Expires</th><th>Volume</th><th>Location</th><th /></tr>
              </thead>
              <tbody>
                {items.map((b) => {
                  const locked = ["dispatched", "discarded"].includes(b.effective_status);
                  const noEdit = locked || b.effective_status === "expired";
                  return (
                    <tr key={b.bag_id} className={b.effective_status === "expired" ? "row-expired" : ""}>
                      <td className="mono bold">{b.bag_id}</td>
                      <td><GroupPill group={b.blood_group} /></td>
                      <td><BagStatusBadge status={b.effective_status} /></td>
                      <td>{fmtDate(b.collection_date)}</td>
                      <td>
                        {fmtDate(b.expiry_date)}
                        {b.effective_status === "available" && (
                          <div className="muted small">{b.days_to_expiry === 0 ? "expires today" : `in ${b.days_to_expiry} days`}</div>
                        )}
                      </td>
                      <td>{b.volume_ml ? `${b.volume_ml} ml` : "—"}</td>
                      <td className="muted">{b.location}</td>
                      <td>
                        <div className="cell-actions">
                          <button className="btn sm" disabled={noEdit} onClick={() => setEditing(b)} aria-label={`Edit ${b.bag_id}`}><Pencil size={14} /> Edit</button>
                          <button className="btn sm danger" disabled={locked} onClick={() => setDiscarding(b)} aria-label={`Discard ${b.bag_id}`}><Trash2 size={14} /></button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {data && (
          <div className="table-foot">
            <span>Showing {data.count} of {data.total} bags</span>
            <span className="spacer" />
            <span>
              <b>{data.sort.name}</b> · {data.sort.comparisons} comparisons · {data.sort.time} · {data.sort.stable ? "stable" : "not stable"}
            </span>
          </div>
        )}
      </div>

      <LookupCard />

      {editing && (
        <BagForm
          bag={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={(msg) => { setEditing(null); toast(msg); reload(); }}
        />
      )}
      {discarding && (
        <ConfirmDialog
          danger
          busy={busy}
          title="Discard this bag?"
          message={`${discarding.bag_id} (${discarding.blood_group}) will be marked as discarded and can never be allocated. This cannot be undone.`}
          confirmLabel="Discard bag"
          onCancel={() => setDiscarding(null)}
          onConfirm={discard}
        />
      )}
    </>
  );
}

/* ---------- Add / edit form ---------- */
function BagForm({ bag, onClose, onSaved }) {
  const isNew = !bag;
  const [v, setV] = useState({
    bag_id: "",
    blood_group: bag?.blood_group || "O+",
    collection_date: bag?.collection_date || todayPlus(0),
    expiry_date: bag?.expiry_date || todayPlus(35),
    volume_ml: bag?.volume_ml ?? 450,
    location: bag?.location || "Central Blood Bank",
    status: bag?.status === "reserved" ? "reserved" : "available",
  });
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value });

  const validate = () => {
    const e = {};
    if (!v.collection_date) e.collection_date = "Required";
    if (!v.expiry_date) e.expiry_date = "Required";
    if (v.collection_date && v.expiry_date && v.expiry_date <= v.collection_date) e.expiry_date = "Expiry date must be later than the collection date";
    if (!v.location.trim()) e.location = "Required";
    const vol = Number(v.volume_ml);
    if (v.volume_ml !== "" && (!Number.isInteger(vol) || vol < 50 || vol > 1000)) e.volume_ml = "Enter 50–1000 ml";
    if (isNew && v.bag_id && !/^[A-Za-z0-9-]{3,20}$/.test(v.bag_id.trim())) e.bag_id = "3–20 letters, digits or dashes";
    return e;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;
    setSaving(true);
    try {
      const volume = v.volume_ml === "" ? null : Number(v.volume_ml);
      if (isNew) {
        const saved = await api.post("/inventory", {
          bag_id: v.bag_id.trim() || null, blood_group: v.blood_group, collection_date: v.collection_date,
          expiry_date: v.expiry_date, volume_ml: volume, location: v.location,
        });
        onSaved(`Bag ${saved.bag_id} added to the ${saved.blood_group} FEFO heap`);
      } else {
        await api.patch(`/inventory/${bag.bag_id}`, {
          collection_date: v.collection_date, expiry_date: v.expiry_date, volume_ml: volume, location: v.location, status: v.status,
        });
        onSaved(`Bag ${bag.bag_id} updated`);
      }
    } catch (err) {
      const fields = { ...err.fields };
      if (fields.request) { fields.expiry_date = fields.request; delete fields.request; }
      setErrors(Object.keys(fields).length ? fields : { form: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={isNew ? "Add blood bag" : `Edit ${bag.bag_id}`}
      onClose={onClose}
      footer={
        <>
          <button className="btn" type="button" onClick={onClose}>Cancel</button>
          <button className="btn primary" form="bag-form" disabled={saving}>{saving && <Loader2 size={16} className="spin" />} {isNew ? "Add bag" : "Save changes"}</button>
        </>
      }
    >
      <form id="bag-form" onSubmit={submit} noValidate>
        {errors.form && <div className="alert bad" role="alert" style={{ marginBottom: 14 }}>{errors.form}</div>}
        <div className="form-grid">
          {isNew && (
            <Field label="Bag ID" error={errors.bag_id} hint="Leave blank to auto-generate (BAG-1017, …)">
              <input className={`input ${errors.bag_id ? "invalid" : ""}`} value={v.bag_id} onChange={set("bag_id")} placeholder="e.g. BAG-2001" />
            </Field>
          )}
          <Field label="Blood group" hint={isNew ? undefined : "Group cannot be changed after registration"}>
            <select className="select" value={v.blood_group} onChange={set("blood_group")} disabled={!isNew}>
              {BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}
            </select>
          </Field>
          <Field label="Collection date" error={errors.collection_date}>
            <input type="date" className={`input ${errors.collection_date ? "invalid" : ""}`} value={v.collection_date} onChange={set("collection_date")} />
          </Field>
          <Field label="Expiry date" error={errors.expiry_date}>
            <input type="date" className={`input ${errors.expiry_date ? "invalid" : ""}`} value={v.expiry_date} onChange={set("expiry_date")} />
          </Field>
          <Field label="Volume (ml)" error={errors.volume_ml}>
            <input type="number" className={`input ${errors.volume_ml ? "invalid" : ""}`} value={v.volume_ml} onChange={set("volume_ml")} />
          </Field>
          <Field label="Location" error={errors.location}>
            <input className={`input ${errors.location ? "invalid" : ""}`} value={v.location} onChange={set("location")} />
          </Field>
          {!isNew && (
            <Field label="Status" hint="Reserved bags are held back from allocation">
              <select className="select" value={v.status} onChange={set("status")}>
                <option value="available">Available</option>
                <option value="reserved">Reserved</option>
              </select>
            </Field>
          )}
        </div>
      </form>
    </Modal>
  );
}

/* ---------- Search algorithm comparison ---------- */
function LookupCard() {
  const [id, setId] = useState("BAG-1010");
  const [method, setMethod] = useState("hash");
  const [res, setRes] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.post("/dsa/search-demo", { method, bag_id: id }));
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card" style={{ marginTop: 18 }}>
      <div className="card-head">
        <h3><SearchCheck size={17} /> Exact bag lookup</h3>
        <span className="muted small">pick the search algorithm and compare the work done</span>
      </div>
      <div className="card-body">
        <form className="row" onSubmit={run}>
          <input className="input" style={{ maxWidth: 220 }} value={id} onChange={(e) => setId(e.target.value)} placeholder="Bag ID" aria-label="Bag ID to look up" />
          <div className="seg" role="group" aria-label="Search method">
            {[["linear", "Linear Search"], ["binary", "Binary Search"], ["hash", "Hash Table"]].map(([k, l]) => (
              <button type="button" key={k} className={method === k ? "on" : ""} onClick={() => setMethod(k)}>{l}</button>
            ))}
          </div>
          <button className="btn primary" disabled={busy || !id.trim()}>{busy && <Loader2 size={16} className="spin" />} Look up</button>
        </form>
        {err && <div className="alert bad" style={{ marginTop: 12 }}>{err}</div>}
        {res && (
          <div style={{ marginTop: 14 }}>
            <div className="stat-row">
              <div className="stat"><b>{res.found ? "Found" : "Not found"}</b><span>result in {res.n} bags</span></div>
              <div className="stat"><b>{res.comparisons}</b><span>{res.method === "hash" ? "chain nodes visited" : "search comparisons"}</span></div>
              {res.method === "binary" && <div className="stat"><b>{res.sort_comparisons}</b><span>sort comparisons (needed first)</span></div>}
              <div className="stat"><b>{res.total_comparisons}</b><span>total work</span></div>
            </div>
            <p className="muted small" style={{ marginTop: 10 }}>
              <b>Precondition:</b> {res.precondition}. <b>Complexity:</b> {res.complexity}.
              {res.found && <> Match: <span className="mono">{res.bag.bag_id}</span> ({res.bag.blood_group}, {res.bag.effective_status}).</>}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
