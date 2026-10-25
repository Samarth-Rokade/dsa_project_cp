import { AlertTriangle, Droplets, ListOrdered, Network, PackageCheck, Trash2 } from "lucide-react";
import { GroupPill, ResultBadge, UrgencyBadge } from "./ui.jsx";
import { fmtDate } from "../api.js";

/** Step-by-step explanation of ONE "Process Next Request" call. */
export default function ProcessResult({ data }) {
  const r = data.request;
  const title = {
    fulfilled: "Request fulfilled",
    partially_fulfilled: "Partially fulfilled",
    no_stock: "No compatible stock",
  }[data.result];

  return (
    <div className={`result ${data.result}`} aria-live="polite">
      <div className="result-head">
        <div className="row">
          <strong style={{ fontSize: 16 }}>{title}</strong>
          <ResultBadge result={data.result} />
        </div>
        <div className="row">
          <span className="mono bold">{r.request_id}</span>
          <span className="muted">{r.hospital_name}</span>
          <GroupPill group={r.required_blood_group} />
          <UrgencyBadge level={r.urgency_level} />
        </div>
      </div>

      <div className="steps">
        {data.expired_removed.length > 0 && (
          <div className="step">
            <div className="step-num"><Trash2 size={13} /></div>
            <div>
              <div className="step-title">Expired stock removed first</div>
              <div className="step-body">Expired bags are never allocated.</div>
              <div className="chips">
                {data.expired_removed.map((id) => <span key={id} className="chip mono">{id}</span>)}
              </div>
            </div>
          </div>
        )}

        <div className="step">
          <div className="step-num"><ListOrdered size={13} /></div>
          <div>
            <div className="step-title">Why this request?</div>
            <div className="step-body">{data.priority_reason}</div>
            {data.skipped_requests.length > 0 && (
              <div className="chips">
                {data.skipped_requests.map((s) => (
                  <span key={s.request_id} className="chip">
                    <b className="mono">{s.request_id}</b> skipped · {s.reason}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="step">
          <div className="step-num"><Network size={13} /></div>
          <div>
            <div className="step-title">
              Compatible donor groups considered ({data.compatibility_mode === "exact" ? "exact match only" : "educational table"})
            </div>
            <div className="chips">
              {data.groups_considered.map((g) => <GroupPill key={g} group={g} on={g === r.required_blood_group} />)}
            </div>
          </div>
        </div>

        <div className="step">
          <div className="step-num"><Droplets size={13} /></div>
          <div>
            <div className="step-title">Bags chosen by FEFO (earliest expiry first)</div>
            {data.allocated_bags.length === 0 ? (
              <div className="step-body">No bag could be allocated.</div>
            ) : (
              <div className="chips">
                {data.allocated_bags.map((b, i) => (
                  <span key={b.bag_id} className="chip">
                    <b>{i + 1}.</b> <span className="mono">{b.bag_id}</span> <GroupPill group={b.blood_group} />
                    <span className="muted">exp {fmtDate(b.expiry_date)}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="step">
          <div className="step-num"><PackageCheck size={13} /></div>
          <div>
            <div className="step-title">Outcome</div>
            <div className="step-body">
              {data.units_allocated_now} unit(s) allocated in this step. Request total so far:{" "}
              {r.units_allocated} of {r.units_needed}.
            </div>
          </div>
        </div>

        {data.shortage_message && (
          <div className="alert warn">
            <AlertTriangle size={18} style={{ flexShrink: 0 }} />
            <div>
              <b>{data.shortage_message}</b> The request stays in the priority queue with its original arrival
              position until more compatible stock is added.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
