import { useEffect, useState } from "react";
import { CalendarClock, Loader2, RotateCcw, ShieldAlert, ShieldCheck } from "lucide-react";
import { api } from "../api.js";
import { ConfirmDialog, ErrorBanner, Field, LoadingBlock, PageHead, useAsync, useToast } from "../components/ui.jsx";

export default function Settings() {
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(() => api.get("/settings"));
  const [days, setDays] = useState(7);
  const [mode, setMode] = useState("educational");
  const [saving, setSaving] = useState(false);
  const [fieldError, setFieldError] = useState("");
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    if (data) { setDays(data.expiring_soon_days); setMode(data.compatibility_mode); }
  }, [data]);

  const save = async (e) => {
    e.preventDefault();
    const n = Number(days);
    if (!Number.isInteger(n) || n < 1 || n > 60) { setFieldError("Enter a whole number from 1 to 60"); return; }
    setFieldError("");
    setSaving(true);
    try {
      await api.put("/settings", { expiring_soon_days: n, compatibility_mode: mode });
      toast("Settings saved");
      reload();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    setResetting(true);
    try {
      const r = await api.post("/admin/reset-demo");
      toast(`Demo data restored: ${r.bags} bags, ${r.requests} requests`);
      setConfirmReset(false);
      reload();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setResetting(false);
    }
  };

  return (
    <>
      <PageHead title="Settings" subtitle="Configurable rules and demo controls." />
      <ErrorBanner error={error} onRetry={reload} />
      {loading && !data ? <div className="card"><LoadingBlock rows={3} /></div> : (
        <div className="grid grid-2">
          <form className="card" onSubmit={save}>
            <div className="card-head"><h3><CalendarClock size={17} /> Allocation rules</h3></div>
            <div className="card-body stack">
              <Field label="Expiry warning window (days)" error={fieldError} hint="Bags expiring within this many days are shown as 'expiring soon'.">
                <input type="number" className={`input ${fieldError ? "invalid" : ""}`} value={days} onChange={(e) => setDays(e.target.value)} />
              </Field>
              <Field label="Blood-group compatibility mode">
                <div className="stack" style={{ gap: 10 }} role="radiogroup">
                  {[
                    ["educational", "Simplified educational table", "Allows donor groups from the teaching compatibility matrix (e.g. O− stock for many requests)."],
                    ["exact", "Exact match only", "Safest fallback: a request may only use stock of exactly the same blood group."],
                  ].map(([k, title, text]) => (
                    <label key={k} className="tile" style={{ cursor: "pointer", display: "flex", gap: 10, borderColor: mode === k ? "var(--primary)" : undefined, background: mode === k ? "var(--primary-50)" : undefined }}>
                      <input type="radio" name="mode" checked={mode === k} onChange={() => setMode(k)} />
                      <span><b>{title}</b><br /><span className="muted small">{text}</span></span>
                    </label>
                  ))}
                </div>
              </Field>
              <div><button className="btn primary" disabled={saving}>{saving && <Loader2 size={16} className="spin" />} Save settings</button></div>
            </div>
          </form>

          <div className="stack">
            <section className="card">
              <div className="card-head"><h3><RotateCcw size={17} /> Demo data</h3></div>
              <div className="card-body stack">
                <p className="muted">Deletes every bag, request and dispatch record and loads the synthetic demo data again (16 bags, 7 requests). Use it to replay the walkthrough from the beginning.</p>
                <div><button className="btn danger" onClick={() => setConfirmReset(true)}><RotateCcw size={16} /> Reset demo data</button></div>
              </div>
            </section>
            <section className="card">
              <div className="card-head"><h3><ShieldAlert size={17} /> Scope notice</h3></div>
              <div className="card-body">
                <div className="alert warn"><ShieldCheck size={18} style={{ flexShrink: 0 }} /><span>{data?.disclaimer}</span></div>
              </div>
            </section>
          </div>
        </div>
      )}
      {confirmReset && (
        <ConfirmDialog
          danger busy={resetting}
          title="Reset all demo data?"
          message="This permanently deletes all current inventory, requests and dispatch records and restores the original demo records."
          confirmLabel="Yes, reset everything"
          onCancel={() => setConfirmReset(false)}
          onConfirm={reset}
        />
      )}
    </>
  );
}
