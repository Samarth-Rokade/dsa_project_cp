import { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  AlertOctagon, AlertTriangle, CheckCircle2, Clock, Inbox, Loader2, PackageCheck, PackageX,
  Scissors, X, XCircle, CircleDashed, CircleDot, Ban, Hourglass, Trash2, Truck, Lock,
} from "lucide-react";

/* ---------- Blood drop logo ---------- */
export function BloodDrop({ size = 24, color = "#fff" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      <path d="M32 4C32 4 12 26 12 40a20 20 0 0 0 40 0C52 26 32 4 32 4z" fill={color} />
    </svg>
  );
}

/* ---------- Toasts ---------- */
const ToastContext = createContext(() => {});
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const push = useCallback((message, type = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>
            {t.type === "error" ? <XCircle size={18} /> : <CheckCircle2 size={18} />}
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ---------- Modal + confirm ---------- */
export function Modal({ title, onClose, children, footer, small }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${small ? "sm" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="btn icon sm" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function ConfirmDialog({ title, message, confirmLabel = "Confirm", danger, busy, onConfirm, onCancel }) {
  return (
    <Modal
      small
      title={title}
      onClose={onCancel}
      footer={
        <>
          <button className="btn" onClick={onCancel}>Cancel</button>
          <button className={`btn ${danger ? "danger" : "primary"}`} onClick={onConfirm} disabled={busy}>
            {busy && <Loader2 size={16} className="spin" />} {confirmLabel}
          </button>
        </>
      }
    >
      <p>{message}</p>
    </Modal>
  );
}

/* ---------- Badges (icon + text, never colour alone) ---------- */
export function UrgencyBadge({ level }) {
  const map = {
    1: { label: "Critical", cls: "rose", Icon: AlertOctagon },
    2: { label: "Surgery", cls: "amber", Icon: Scissors },
    3: { label: "Routine", cls: "slate", Icon: Clock },
  };
  const { label, cls, Icon } = map[level];
  return <span className={`badge ${cls}`}><Icon size={13} /> {level} · {label}</span>;
}

export function RequestStatusBadge({ status }) {
  const map = {
    pending: { label: "Pending", cls: "slate", Icon: Hourglass },
    partially_fulfilled: { label: "Partially fulfilled", cls: "amber", Icon: CircleDot },
    fulfilled: { label: "Fulfilled", cls: "green", Icon: CheckCircle2 },
    cancelled: { label: "Cancelled", cls: "rose", Icon: Ban },
  };
  const { label, cls, Icon } = map[status];
  return <span className={`badge ${cls}`}><Icon size={13} /> {label}</span>;
}

export function BagStatusBadge({ status }) {
  const map = {
    available: { label: "Available", cls: "green", Icon: PackageCheck },
    reserved: { label: "Reserved", cls: "blue", Icon: Lock },
    dispatched: { label: "Dispatched", cls: "violet", Icon: Truck },
    expired: { label: "Expired", cls: "rose", Icon: PackageX },
    discarded: { label: "Discarded", cls: "slate", Icon: Trash2 },
  };
  const { label, cls, Icon } = map[status];
  return <span className={`badge ${cls}`}><Icon size={13} /> {label}</span>;
}

export function ResultBadge({ result }) {
  const map = {
    fulfilled: { label: "Fulfilled", cls: "green", Icon: CheckCircle2 },
    partially_fulfilled: { label: "Partially fulfilled", cls: "amber", Icon: CircleDot },
    no_stock: { label: "No stock", cls: "rose", Icon: CircleDashed },
  };
  const { label, cls, Icon } = map[result];
  return <span className={`badge ${cls}`}><Icon size={13} /> {label}</span>;
}

export const GroupPill = ({ group, dim, on }) => (
  <span className={`group-pill ${dim ? "dim" : ""} ${on ? "on" : ""}`}>{group}</span>
);

/* ---------- Layout helpers ---------- */
export function PageHead({ title, subtitle, children }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children && <div className="actions">{children}</div>}
    </div>
  );
}

export function KpiCard({ icon: Icon, tone, value, label }) {
  return (
    <div className="card kpi">
      <div className={`kpi-icon tone-${tone}`}><Icon size={22} /></div>
      <div>
        <div className="kpi-value">{value}</div>
        <div className="kpi-label">{label}</div>
      </div>
    </div>
  );
}

export function EmptyState({ icon: Icon = Inbox, title, text }) {
  return (
    <div className="empty">
      <Icon size={38} />
      <h4>{title}</h4>
      {text && <p>{text}</p>}
    </div>
  );
}

export function LoadingBlock({ rows = 5 }) {
  return (
    <div style={{ padding: 20, display: "grid", gap: 12 }} aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: 34 }} />
      ))}
    </div>
  );
}

export function ErrorBanner({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="alert bad" role="alert" style={{ marginBottom: 16 }}>
      <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: 1 }} />
      <div style={{ flex: 1 }}>{error.message || String(error)}</div>
      {onRetry && <button className="btn sm" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Field({ label, error, hint, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {hint && !error && <span className="hint">{hint}</span>}
      {error && <span className="error" role="alert">{error}</span>}
    </div>
  );
}

/* ---------- Data loading hook ---------- */
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      setState({ data: await fn(), loading: false, error: null });
    } catch (error) {
      setState({ data: null, loading: false, error });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { load(); }, [load]);
  return { ...state, reload: load };
}
