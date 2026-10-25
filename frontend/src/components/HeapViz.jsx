/** Draws a binary heap (given as its array) as a tree plus the array itself. */
export function HeapTree({ nodes, maxNodes = 31 }) {
  if (!nodes.length) return <div className="muted small" style={{ padding: 16 }}>The heap is empty.</div>;

  const shown = nodes.slice(0, maxNodes);
  const levels = Math.floor(Math.log2(shown.length)) + 1;
  const W = Math.max(560, 2 ** (levels - 1) * 66);
  const H = levels * 74 + 20;
  const pos = (i) => {
    const level = Math.floor(Math.log2(i + 1));
    const first = 2 ** level - 1;
    return { x: ((i - first + 0.5) / 2 ** level) * W, y: 36 + level * 74 };
  };

  return (
    <div>
      <svg className="heap-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Binary heap drawn as a tree">
        {shown.map((_, i) => {
          if (i === 0) return null;
          const a = pos(i);
          const b = pos(Math.floor((i - 1) / 2));
          return <line key={`l${i}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#cfd3df" strokeWidth="2" />;
        })}
        {shown.map((n, i) => {
          const { x, y } = pos(i);
          const root = i === 0;
          return (
            <g key={i}>
              <circle cx={x} cy={y} r="29" fill={root ? "#e11d48" : "#fff"} stroke={root ? "#be123c" : "#d5d9e4"} strokeWidth="2" />
              <text x={x} y={n.sub ? y - 2 : y + 4} textAnchor="middle" fontSize="11.5" fontWeight="700" fill={root ? "#fff" : "#171923"} fontFamily="JetBrains Mono, monospace">
                {String(n.title).slice(0, 8)}
              </text>
              {n.sub && (
                <text x={x} y={y + 12} textAnchor="middle" fontSize="9.5" fill={root ? "#ffe0e6" : "#667085"} fontFamily="JetBrains Mono, monospace">
                  {n.sub}
                </text>
              )}
              <text x={x} y={y - 35} textAnchor="middle" fontSize="9.5" fill="#98a2b3">[{i}]</text>
            </g>
          );
        })}
      </svg>
      {nodes.length > maxNodes && <p className="muted small">Showing the first {maxNodes} of {nodes.length} nodes in the tree. The full array is below.</p>}
    </div>
  );
}

export function ArrayStrip({ nodes }) {
  if (!nodes.length) return null;
  return (
    <div className="array" style={{ paddingTop: 10 }}>
      {nodes.map((n, i) => (
        <div key={i} className={`cell ${i === 0 ? "root" : ""}`}>
          <span className="idx">{i}</span>
          {String(n.title).slice(0, 9)}
          {n.sub && <small>{n.sub}</small>}
        </div>
      ))}
    </div>
  );
}
