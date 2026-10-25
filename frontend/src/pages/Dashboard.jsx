import { Link } from "react-router-dom";
import {
  AlertOctagon, ArrowRight, CalendarClock, Droplets, Hourglass, PackageCheck, PackageX, Siren, Truck,
} from "lucide-react";
import { api, fmtDate, fmtDateTime } from "../api.js";
import {
  BloodDrop, EmptyState, ErrorBanner, GroupPill, KpiCard, LoadingBlock, PageHead, ResultBadge, UrgencyBadge,
  useAsync,
} from "../components/ui.jsx";

export default function Dashboard() {
  const { data, loading, error, reload } = useAsync(() => api.get("/analytics/dashboard"));

  if (error) return <ErrorBanner error={error} onRetry={reload} />;
  if (loading || !data) {
    return (
      <>
        <div className="skeleton" style={{ height: 150, borderRadius: 20, marginBottom: 20 }} />
        <div className="grid grid-3"><div className="skeleton" style={{ height: 84 }} /><div className="skeleton" style={{ height: 84 }} /><div className="skeleton" style={{ height: 84 }} /></div>
      </>
    );
  }

  const { kpis, stock_by_group: stock, expiring_bags: expiring, priority_queue: queue, recent_dispatches: recent, settings } = data;
  const maxStock = Math.max(1, ...stock.map((s) => s.available));

  return (
    <>
      <div className="hero">
        <div className="drop-bg"><BloodDrop size={230} /></div>
        <h1>Prioritize urgent requests. Allocate compatible stock. Reduce expiry waste.</h1>
        <p>
          A priority heap picks the next hospital request, a compatibility table filters eligible stock, and
          First-Expired-First-Out heaps choose the bags that expire soonest.
        </p>
        <Link to="/requests"><button className="btn light"><Siren size={17} /> Open request queue <ArrowRight size={16} /></button></Link>
      </div>

      <div className="grid grid-3" style={{ marginBottom: 20 }}>
        <KpiCard icon={PackageCheck} tone="green" value={kpis.available_units} label="Available, non-expired units" />
        <KpiCard icon={Droplets} tone="blue" value={kpis.registered_bags} label="Registered blood bags" />
        <KpiCard icon={Hourglass} tone="slate" value={kpis.pending_requests} label="Pending requests" />
        <KpiCard icon={AlertOctagon} tone="rose" value={kpis.critical_waiting} label="Critical requests waiting" />
        <KpiCard icon={CalendarClock} tone="amber" value={kpis.expiring_soon} label={`Bags expiring within ${settings.expiring_soon_days} days`} />
        <KpiCard icon={PackageX} tone="violet" value={kpis.expired_units} label="Expired bags (never allocated)" />
      </div>

      <div className="grid grid-main">
        <div className="stack">
          <section className="card">
            <div className="card-head"><h3><Droplets size={17} /> Stock by blood group</h3><span className="muted small">usable units only</span></div>
            <div className="card-body">
              <div className="tiles">
                {stock.map((s) => (
                  <div key={s.blood_group} className={`tile ${s.available === 0 ? "low" : ""}`}>
                    <div className="tile-group"><GroupPill group={s.blood_group} /></div>
                    <div className="tile-count">{s.available}</div>
                    <div className="tile-meta">
                      {s.available === 0 ? "Out of stock" : s.expiring_soon > 0 ? `${s.expiring_soon} expiring soon` : "units available"}
                    </div>
                    <div className="bar"><span style={{ width: `${(s.available / maxStock) * 100}%` }} /></div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="card">
            <div className="card-head">
              <h3><CalendarClock size={17} /> Expiry warnings</h3>
              <span className="muted small">sorted by Merge Sort, earliest first</span>
            </div>
            {expiring.length === 0 ? (
              <EmptyState icon={PackageCheck} title="Nothing is about to expire" text="No available bag expires inside the warning window." />
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Bag</th><th>Group</th><th>Expires</th><th>Time left</th><th>Location</th></tr></thead>
                  <tbody>
                    {expiring.map((b) => (
                      <tr key={b.bag_id}>
                        <td className="mono bold">{b.bag_id}</td>
                        <td><GroupPill group={b.blood_group} /></td>
                        <td>{fmtDate(b.expiry_date)}</td>
                        <td><span className="badge amber"><CalendarClock size={12} /> {b.days_to_expiry === 0 ? "today" : `${b.days_to_expiry} day${b.days_to_expiry === 1 ? "" : "s"}`}</span></td>
                        <td className="muted">{b.location}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>

        <div className="stack">
          <section className="card">
            <div className="card-head"><h3><Siren size={17} /> Priority queue</h3><span className="muted small">live heap order</span></div>
            {queue.length === 0 ? (
              <EmptyState icon={Siren} title="Queue is empty" text="Create a hospital request to see it here." />
            ) : (
              <div className="list">
                {queue.map((q) => (
                  <div key={q.request_id} className="list-item">
                    <div className={`rank ${q.queue_position === 1 ? "first" : ""}`}>{q.queue_position}</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="bold" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{q.hospital_name}</div>
                      <div className="muted small"><span className="mono">{q.request_id}</span> · {q.units_remaining} unit(s) · arrival #{q.arrival_sequence}</div>
                    </div>
                    <GroupPill group={q.required_blood_group} />
                    <UrgencyBadge level={q.urgency_level} />
                  </div>
                ))}
              </div>
            )}
            <div className="table-foot"><Link to="/requests">Manage requests →</Link></div>
          </section>

          <section className="card">
            <div className="card-head"><h3><Truck size={17} /> Recent dispatches</h3></div>
            {recent.length === 0 ? (
              <EmptyState icon={Truck} title="No dispatches yet" text="Process a request to create the first record." />
            ) : (
              <div className="list">
                {recent.map((d) => (
                  <div key={d.id} className="list-item">
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="bold" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{d.hospital_name}</div>
                      <div className="muted small">
                        <span className="mono">{d.request_id}</span> · {d.units_allocated}/{d.units_requested} units · {fmtDateTime(d.processed_at)}
                      </div>
                    </div>
                    <ResultBadge result={d.result} />
                  </div>
                ))}
              </div>
            )}
            <div className="table-foot"><Link to="/dispatches">Full history →</Link></div>
          </section>
        </div>
      </div>
    </>
  );
}
