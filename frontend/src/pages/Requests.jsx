import { useEffect, useState } from "react";
import { AlertOctagon, Ban, Clock, Loader2, Play, Plus, Scissors, Search, Siren } from "lucide-react";
import { api, BLOOD_GROUPS, fmtDateTime } from "../api.js";
import ProcessResult from "../components/ProcessResult.jsx";
import {
  ConfirmDialog, EmptyState, ErrorBanner, Field, GroupPill, LoadingBlock, Modal, PageHead, RequestStatusBadge,
  UrgencyBadge, useAsync, useToast,
} from "../components/ui.jsx";

export default function Requests() {
  const toast = useToast();
  const [f, setF] = useState({ search: "", status: "", urgency: "", sort_by: "priority", order: "asc" });
  const [debounced, setDebounced] = useState("");
  const [creating, setCreating] = useState(false);
  const [cancelling, setCancelling] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(f.search), 250);
    return () => clearTimeout(t);
  }, [f.search]);

  const { data, loading, error, reload } = useAsync(
    () => api.get("/requests", { ...f, search: debounced }),
    [debounced, f.status, f.urgency, f.sort_by, f.order]
  );
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const items = data?.items || [];

  const processNext = async () => {
    setProcessing(true);
    try {
      const r = await api.post("/requests/process-next");
      setResult(r);
      toast(
        r.result === "fulfilled" ? `${r.request.request_id} fulfilled`
          : r.result === "partially_fulfilled" ? `${r.request.request_id} partially fulfilled`
          : `No compatible stock for ${r.request.request_id}`,
        r.result === "no_stock" ? "error" : "success"
      );
      reload();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setProcessing(false);
    }
  };

  const cancel = async () => {
    setBusy(true);
    try {
      await api.patch(`/requests/${cancelling.request_id}/cancel`);
      toast(`${cancelling.request_id} cancelled`);
      setCancelling(null);
      reload();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHead
        title="Hospital Requests"
        subtitle="Requests wait in a binary heap ordered by urgency (1 = most urgent) and then by arrival. One click processes exactly one request."
      >
        <button className="btn" onClick={() => setCreating(true)}><Plus size={16} /> New request</button>
        <button className="btn primary" onClick={processNext} disabled={processing}>
          {processing ? <Loader2 size={16} className="spin" /> : <Play size={16} />} Process next request
        </button>
      </PageHead>

      <ErrorBanner error={error} onRetry={reload} />

      {result && (
        <div style={{ marginBottom: 18, position: "relative" }}>
          <ProcessResult data={result} />
          <div style={{ textAlign: "right", marginTop: 6 }}>
            <button className="btn sm" onClick={() => setResult(null)}>Dismiss explanation</button>
          </div>
        </div>
      )}

      <div className="card">
        <div className="filters">
          <div className="search-wrap">
            <Search size={16} />
            <input className="input" placeholder="Search request ID or hospital…" value={f.search} onChange={set("search")} aria-label="Search requests" />
          </div>
          <select className="select" value={f.status} onChange={set("status")} aria-label="Status">
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="partially_fulfilled">Partially fulfilled</option>
            <option value="fulfilled">Fulfilled</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <select className="select" value={f.urgency} onChange={set("urgency")} aria-label="Urgency">
            <option value="">All urgency levels</option>
            <option value="1">1 · Critical</option>
            <option value="2">2 · Surgery</option>
            <option value="3">3 · Routine</option>
          </select>
          <span className="spacer" />
          <select className="select" value={f.sort_by} onChange={set("sort_by")} aria-label="Sort by">
            <option value="priority">Sort: priority</option>
            <option value="arrival">Sort: arrival order</option>
            <option value="units_needed">Sort: units needed</option>
          </select>
          <div className="seg" role="group" aria-label="Order">
            <button className={f.order === "asc" ? "on" : ""} onClick={() => setF({ ...f, order: "asc" })}>Asc</button>
            <button className={f.order === "desc" ? "on" : ""} onClick={() => setF({ ...f, order: "desc" })}>Desc</button>
          </div>
        </div>

        {loading && !data ? (
          <LoadingBlock />
        ) : items.length === 0 ? (
          <EmptyState icon={Siren} title="No requests found" text="Create a request or relax the filters." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Queue</th><th>Request</th><th>Hospital</th><th>Needs</th><th>Fulfilled</th><th>Urgency</th><th>Arrival</th><th>Status</th><th /></tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.request_id}>
                    <td>
                      {r.queue_position ? (
                        <span className={`rank ${r.queue_position === 1 ? "first" : ""}`} title="Position in the priority heap">{r.queue_position}</span>
                      ) : <span className="muted">—</span>}
                    </td>
                    <td className="mono bold">{r.request_id}</td>
                    <td>
                      <div className="bold">{r.hospital_name}</div>
                      {r.notes && <div className="muted small">{r.notes}</div>}
                    </td>
                    <td>
                      <div className="row" style={{ gap: 8 }}><GroupPill group={r.required_blood_group} /><b>{r.units_needed}</b></div>
                      <div className="muted small">accepts {r.compatible_groups.join(", ")}</div>
                    </td>
                    <td style={{ minWidth: 110 }}>
                      <b>{r.units_allocated}</b> / {r.units_needed}
                      <div className="bar"><span style={{ width: `${(r.units_allocated / r.units_needed) * 100}%` }} /></div>
                    </td>
                    <td><UrgencyBadge level={r.urgency_level} /></td>
                    <td className="muted">#{r.arrival_sequence}<div className="small">{fmtDateTime(r.created_at)}</div></td>
                    <td><RequestStatusBadge status={r.status} /></td>
                    <td>
                      <div className="cell-actions">
                        {(r.status === "pending" || r.status === "partially_fulfilled") && (
                          <button className="btn sm danger" onClick={() => setCancelling(r)} aria-label={`Cancel ${r.request_id}`}><Ban size={14} /> Cancel</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="table-foot">
          <span>{items.length} request(s)</span>
          <span className="spacer" />
          <span>Sorted with Merge Sort · priority = (urgency, arrival sequence, request ID)</span>
        </div>
      </div>

      {creating && <RequestForm onClose={() => setCreating(false)} onSaved={(r) => { setCreating(false); toast(`${r.request_id} created — queue position ${r.queue_position}`); reload(); }} />}
      {cancelling && (
        <ConfirmDialog
          danger busy={busy}
          title="Cancel this request?"
          message={`${cancelling.request_id} from ${cancelling.hospital_name} will leave the priority queue. Bags already dispatched for it stay dispatched.`}
          confirmLabel="Cancel request"
          onCancel={() => setCancelling(null)}
          onConfirm={cancel}
        />
      )}
    </>
  );
}

const URGENCY_OPTIONS = [
  { v: 1, label: "Critical", sub: "Trauma / life-threatening", Icon: AlertOctagon },
  { v: 2, label: "Surgery", sub: "Planned or urgent surgery", Icon: Scissors },
  { v: 3, label: "Routine", sub: "Normal stock top-up", Icon: Clock },
];

function RequestForm({ onClose, onSaved }) {
  const [v, setV] = useState({ hospital_name: "", required_blood_group: "A+", units_needed: 2, urgency_level: 2, notes: "" });
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value });

  const validate = () => {
    const e = {};
    if (v.hospital_name.trim().length < 2) e.hospital_name = "Enter the hospital name (at least 2 characters)";
    const n = Number(v.units_needed);
    if (!Number.isInteger(n) || n < 1 || n > 50) e.units_needed = "Units must be a whole number from 1 to 50";
    return e;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;
    setSaving(true);
    try {
      onSaved(await api.post("/requests", {
        hospital_name: v.hospital_name, required_blood_group: v.required_blood_group,
        units_needed: Number(v.units_needed), urgency_level: v.urgency_level, notes: v.notes.trim() || null,
      }));
    } catch (err) {
      setErrors(Object.keys(err.fields).length ? err.fields : { form: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title="New hospital request"
      onClose={onClose}
      footer={
        <>
          <button className="btn" type="button" onClick={onClose}>Cancel</button>
          <button className="btn primary" form="req-form" disabled={saving}>{saving && <Loader2 size={16} className="spin" />} Create request</button>
        </>
      }
    >
      <form id="req-form" onSubmit={submit} noValidate>
        {errors.form && <div className="alert bad" role="alert" style={{ marginBottom: 14 }}>{errors.form}</div>}
        <div className="form-grid">
          <div className="full">
            <Field label="Hospital name" error={errors.hospital_name}>
              <input className={`input ${errors.hospital_name ? "invalid" : ""}`} value={v.hospital_name} onChange={set("hospital_name")} placeholder="e.g. City General Hospital" autoFocus />
            </Field>
          </div>
          <Field label="Required blood group">
            <select className="select" value={v.required_blood_group} onChange={set("required_blood_group")}>
              {BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}
            </select>
          </Field>
          <Field label="Units needed" error={errors.units_needed}>
            <input type="number" min="1" className={`input ${errors.units_needed ? "invalid" : ""}`} value={v.units_needed} onChange={set("units_needed")} />
          </Field>
          <div className="full">
            <Field label="Urgency level" error={errors.urgency_level}>
              <div className="grid grid-3" style={{ gap: 10 }} role="radiogroup" aria-label="Urgency level">
                {URGENCY_OPTIONS.map(({ v: lvl, label, sub, Icon }) => (
                  <button
                    type="button" key={lvl} role="radio" aria-checked={v.urgency_level === lvl}
                    onClick={() => setV({ ...v, urgency_level: lvl })}
                    className="tile" style={{
                      textAlign: "left", cursor: "pointer", font: "inherit",
                      borderColor: v.urgency_level === lvl ? "var(--primary)" : undefined,
                      boxShadow: v.urgency_level === lvl ? "0 0 0 3px var(--primary-100)" : undefined,
                      background: v.urgency_level === lvl ? "var(--primary-50)" : undefined,
                    }}
                  >
                    <div className="row" style={{ gap: 6 }}><Icon size={16} /><b>{lvl} · {label}</b></div>
                    <div className="muted small">{sub}</div>
                  </button>
                ))}
              </div>
            </Field>
          </div>
          <div className="full">
            <Field label="Notes (optional)" error={errors.notes} hint="Do not enter patient names or any identifying details.">
              <textarea className="textarea" rows={2} maxLength={200} value={v.notes} onChange={set("notes")} />
            </Field>
          </div>
        </div>
      </form>
    </Modal>
  );
}
