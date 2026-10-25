import { Fragment, useState } from "react";
import { ChevronDown, ChevronRight, History } from "lucide-react";
import { api, fmtDate, fmtDateTime } from "../api.js";
import {
  EmptyState, ErrorBanner, GroupPill, LoadingBlock, PageHead, ResultBadge, UrgencyBadge, useAsync,
} from "../components/ui.jsx";

export default function Dispatches() {
  const [order, setOrder] = useState("desc");
  const [result, setResult] = useState("");
  const [open, setOpen] = useState(null);
  const { data, loading, error, reload } = useAsync(() => api.get("/dispatches", { order, result }), [order, result]);
  const items = data?.items || [];

  return (
    <>
      <PageHead title="Dispatch History" subtitle="An append-only log of every processing attempt. Records can be inspected but never edited. Sorted by time with Merge Sort.">
        <select className="select" style={{ width: "auto" }} value={result} onChange={(e) => setResult(e.target.value)} aria-label="Result filter">
          <option value="">All results</option>
          <option value="fulfilled">Fulfilled</option>
          <option value="partially_fulfilled">Partially fulfilled</option>
          <option value="no_stock">No stock</option>
        </select>
        <div className="seg" role="group" aria-label="Time order">
          <button className={order === "desc" ? "on" : ""} onClick={() => setOrder("desc")}>Newest first</button>
          <button className={order === "asc" ? "on" : ""} onClick={() => setOrder("asc")}>Oldest first</button>
        </div>
      </PageHead>

      <ErrorBanner error={error} onRetry={reload} />

      <div className="card">
        {loading && !data ? (
          <LoadingBlock />
        ) : items.length === 0 ? (
          <EmptyState icon={History} title="No dispatches yet" text="Process a hospital request to create the first record." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th /><th>Time</th><th>Request</th><th>Hospital</th><th>Requested</th><th>Allocated bags</th><th>Fulfilled</th><th>Result</th></tr>
              </thead>
              <tbody>
                {items.map((d) => (
                  <Fragment key={d.id}>
                    <tr style={{ cursor: "pointer" }} onClick={() => setOpen(open === d.id ? null : d.id)}>
                      <td>
                        <button className="btn icon sm" aria-label={open === d.id ? "Collapse" : "Expand"} aria-expanded={open === d.id}>
                          {open === d.id ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                        </button>
                      </td>
                      <td className="muted" style={{ whiteSpace: "nowrap" }}>{fmtDateTime(d.processed_at)}</td>
                      <td className="mono bold">{d.request_id}</td>
                      <td>{d.hospital_name}<div><UrgencyBadge level={d.urgency_level} /></div></td>
                      <td><div className="row" style={{ gap: 8 }}><GroupPill group={d.required_blood_group} /><b>{d.units_requested}</b></div></td>
                      <td>
                        {d.bags.length === 0 ? <span className="muted">—</span> : (
                          <div className="row" style={{ gap: 4 }}>
                            {d.bags.map((b) => <span key={b.bag_id} className="chip mono">{b.bag_id}<GroupPill group={b.donor_blood_group} dim /></span>)}
                          </div>
                        )}
                      </td>
                      <td><b>{d.units_allocated}</b> done · <span className={d.units_remaining ? "bold" : "muted"}>{d.units_remaining}</span> left</td>
                      <td><ResultBadge result={d.result} /></td>
                    </tr>
                    {open === d.id && (
                      <tr>
                        <td />
                        <td colSpan={7} style={{ background: "var(--surface-2)" }}>
                          <div className="step-title" style={{ marginBottom: 4 }}>Decision explanation</div>
                          <p className="step-body">{d.decision_summary}</p>
                          <div className="chips">
                            <span className="chip muted">Groups considered:</span>
                            {d.groups_considered.map((g) => <GroupPill key={g} group={g} on={g === d.required_blood_group} />)}
                          </div>
                          {d.bags.length > 0 && (
                            <div className="chips">
                              {d.bags.map((b) => (
                                <span key={b.bag_id} className="chip">
                                  <b className="mono">{b.bag_id}</b> donor <GroupPill group={b.donor_blood_group} /> expiry {fmtDate(b.expiry_date)}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="table-foot">{items.length} record(s)</div>
      </div>
    </>
  );
}
