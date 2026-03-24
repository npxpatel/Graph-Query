import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const FALLBACK_SAMPLE_QUERIES = [
  "Which products are associated with the highest number of billing documents?",
  "Trace the full flow of 740506",
  "Identify sales orders with broken or incomplete flows"
];

let msgId = 0;
const nextId = () => ++msgId;

function formatValue(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function NodeDetailCard({ node, onClose }) {
  if (!node) return null;
  const meta = node.metadata && typeof node.metadata === "object" ? node.metadata : {};
  const entries = Object.entries(meta).filter(([k]) => k && !String(k).startsWith("_"));
  const visible = entries.slice(0, 14);
  const hidden = entries.length - visible.length;

  return (
    <div className="node-detail-card" role="dialog" aria-label="Node details">
      <div className="node-detail-card__header">
        <span className="node-detail-card__entity">{node.entity_type || "Entity"}</span>
        <button type="button" className="node-detail-card__close" onClick={onClose} aria-label="Close details">
          ×
        </button>
      </div>
      <dl className="node-detail-kv">
        <div className="node-detail-kv__row">
          <dt>id</dt>
          <dd>{formatValue(node.id)}</dd>
        </div>
        <div className="node-detail-kv__row">
          <dt>label</dt>
          <dd>{formatValue(node.label)}</dd>
        </div>
        {visible.map(([k, v]) => (
          <div key={k} className="node-detail-kv__row">
            <dt>{k}</dt>
            <dd>{formatValue(v)}</dd>
          </div>
        ))}
      </dl>
      {hidden > 0 ? <p className="node-detail-card__note">Additional fields hidden for readability</p> : null}
    </div>
  );
}

function ResultsTable({ rows }) {
  if (!Array.isArray(rows) || rows.length === 0) return null;
  const cols = Object.keys(rows[0] || {});
  const preview = rows.slice(0, 25);
  return (
    <div className="result-table-wrap">
      <table className="result-table">
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {preview.map((row, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c}>{formatValue(row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > preview.length ? (
        <p className="result-table__more">Showing {preview.length} of {rows.length} rows</p>
      ) : null}
    </div>
  );
}

function AssistantMessage({ msg }) {
  const [open, setOpen] = useState(false);
  const hasDetails = Boolean((msg.sqlQuery && msg.sqlQuery.trim()) || (msg.reasoning && msg.reasoning.trim()));

  return (
    <div className="chat-msg chat-msg--assistant">
      <div className="chat-msg__agent">
        <div className="chat-msg__avatar" aria-hidden="true">
          D
        </div>
        <div>
          <div className="chat-msg__agent-name">Dodge AI</div>
          <div className="chat-msg__agent-role">Graph Agent</div>
        </div>
      </div>
      <div className="chat-msg__body chat-msg__body--assistant">
        <p className="chat-msg__text">{msg.answer}</p>
        {msg.rows?.length ? <ResultsTable rows={msg.rows} /> : null}
        {hasDetails ? (
          <div className="chat-msg__details">
            <button type="button" className="chat-msg__details-toggle" onClick={() => setOpen((o) => !o)}>
              {open ? "Hide technical details" : "Show technical details"}
            </button>
            {open ? (
              <div className="chat-msg__details-panel">
                {msg.intent || msg.guardrail ? (
                  <p>
                    {msg.intent ? (
                      <>
                        <span className="muted">Operation</span> {msg.intent}
                      </>
                    ) : null}
                    {msg.intent && msg.guardrail ? " · " : null}
                    {msg.guardrail ? (
                      <>
                        <span className="muted">Guardrail</span> {msg.guardrail}
                      </>
                    ) : null}
                  </p>
                ) : null}
                {msg.sqlQuery ? (
                  <>
                    <p className="muted small-margin">SQL</p>
                    <pre className="chat-msg__sql">{msg.sqlQuery}</pre>
                  </>
                ) : null}
                {msg.reasoning ? (
                  <>
                    <p className="muted small-margin">Planner notes</p>
                    <p className="chat-msg__reasoning">{msg.reasoning}</p>
                  </>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function App() {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [highlightedNodes, setHighlightedNodes] = useState([]);
  const [fullGraphCache, setFullGraphCache] = useState({ nodes: [], edges: [] });
  const [messages, setMessages] = useState([
    {
      id: nextId(),
      role: "assistant",
      answer: "Hi! I can help you analyze the Order to Cash process.",
      greeting: true
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [graphMinimized, setGraphMinimized] = useState(false);
  const [showGranularOverlay, setShowGranularOverlay] = useState(true);
  const [sampleQueries, setSampleQueries] = useState(FALLBACK_SAMPLE_QUERIES);
  const fgRef = useRef();

  useEffect(() => {
    fetch(`${API_BASE}/examples`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        const list = data?.examples;
        if (Array.isArray(list) && list.length > 0) {
          setSampleQueries(list.slice(0, 3));
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/graph/full`)
      .then((r) => r.json())
      .then((data) => {
        setGraph(data);
        setFullGraphCache(data);
      })
      .catch(() => setGraph({ nodes: [], edges: [] }));
  }, []);

  const expandNode = async (node) => {
    try {
      const [subgraphRes, nodeRes] = await Promise.all([
        fetch(`${API_BASE}/graph/subgraph?center_node_id=${encodeURIComponent(node.id)}&depth=1`),
        fetch(`${API_BASE}/node/${encodeURIComponent(node.id)}`)
      ]);
      const subgraphData = await subgraphRes.json();
      const nodeData = await nodeRes.json();
      if (subgraphData?.graph) setGraph(subgraphData.graph);
      setSelectedNode(nodeData?.node || node);
    } catch {
      setSelectedNode(node);
    }
  };

  const fgData = useMemo(
    () => ({
      nodes: graph.nodes.map((n) => ({ ...n, id: n.id, name: `${n.entity_type}: ${n.label}` })),
      links: graph.edges.map((e, i) => ({ ...e, source: e.source, target: e.target, id: `${e.source}-${e.target}-${i}` }))
    }),
    [graph]
  );

  const runQuery = async (rawQuery, { fromInput = false } = {}) => {
    const query = String(rawQuery).trim();
    if (!query || loading) return;
    setMessages((m) => [...m, { id: nextId(), role: "user", text: query }]);
    if (fromInput) setInput("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });
      const data = await res.json();
      const referenced = data?.evidence?.referenced_nodes;
      if (Array.isArray(referenced) && referenced.length > 0) {
        setHighlightedNodes(referenced);
      } else {
        setHighlightedNodes([]);
      }

      const rows = data.evidence?.rows;
      const sqlQuery = typeof data.evidence?.sql_query === "string" ? data.evidence.sql_query : "";
      const reasoning =
        typeof data.evidence?.planner_reasoning === "string" ? data.evidence.planner_reasoning : "";

      setMessages((m) => [
        ...m,
        {
          id: nextId(),
          role: "assistant",
          answer: data.answer || "No answer returned.",
          rows: Array.isArray(rows) ? rows : [],
          sqlQuery,
          reasoning,
          intent: data.intent || "",
          guardrail: data.guardrail || ""
        }
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          id: nextId(),
          role: "assistant",
          answer: "Request failed. Check that the API server is running and CORS allows this origin.",
          rows: [],
          sqlQuery: "",
          reasoning: "",
          intent: "error",
          guardrail: ""
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const sendQuery = () => runQuery(input, { fromInput: true });

  const resetFullGraph = () => {
    setGraph(fullGraphCache);
    setSelectedNode(null);
    if (fgRef.current) {
      fgRef.current.zoomToFit?.(400, 50);
    }
  };

  return (
    <div className="shell">
      <header className="top-nav">
        <div className="top-nav__left">
          <button type="button" className="icon-btn" aria-label="Toggle sidebar" title="Sidebar">
            <span className="icon-sidebar" />
          </button>
          <nav className="breadcrumb" aria-label="Breadcrumb">
            <span className="breadcrumb__muted">Mapping</span>
            <span className="breadcrumb__sep">/</span>
            <span className="breadcrumb__current">Order to Cash</span>
          </nav>
        </div>
        <button type="button" className="icon-btn icon-btn--round" aria-label="More options">
          <span className="icon-dots">⋯</span>
        </button>
      </header>

      <div className="body">
        <section className={`graph-pane ${graphMinimized ? "graph-pane--minimized" : ""}`}>
          <div className="graph-toolbar">
            <button
              type="button"
              className="pill-btn"
              onClick={() => setGraphMinimized((v) => !v)}
              title={graphMinimized ? "Expand graph" : "Minimize graph"}
            >
              <span className="pill-btn__icon pill-btn__icon--minimize" aria-hidden="true" />
              {graphMinimized ? "Expand" : "Minimize"}
            </button>
            <button
              type="button"
              className="pill-btn pill-btn--dark"
              onClick={() => setShowGranularOverlay((v) => !v)}
              title="Toggle labels and detail on the graph"
            >
              <span className="pill-btn__icon pill-btn__icon--layers" aria-hidden="true" />
              {showGranularOverlay ? "Hide Granular Overlay" : "Show Granular Overlay"}
            </button>
            <button type="button" className="pill-btn pill-btn--ghost" onClick={resetFullGraph}>
              Reset graph
            </button>
          </div>

          <div className="graph-stage">
            {!graphMinimized ? (
              <>
                <ForceGraph2D
                  ref={fgRef}
                  graphData={fgData}
                  backgroundColor="rgba(0,0,0,0)"
                  nodeLabel={(node) => node.name}
                  linkDirectionalArrowLength={showGranularOverlay ? 4 : 0}
                  linkDirectionalArrowRelPos={1}
                  linkColor={() => (showGranularOverlay ? "#a5d8ff" : "#d4d4d8")}
                  linkWidth={() => (showGranularOverlay ? 0.9 : 0.45)}
                  onNodeClick={expandNode}
                  nodeCanvasObject={(node, ctx, globalScale) => {
                    const r = showGranularOverlay ? 4.2 : 3;
                    const isHi = highlightedNodes.includes(node.id);
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
                    ctx.fillStyle = isHi ? "#e11d48" : "#3b82f6";
                    ctx.fill();
                    if (showGranularOverlay) {
                      const fontSize = Math.max(8, 10 / globalScale);
                      ctx.font = `${fontSize}px "DM Sans", system-ui, sans-serif`;
                      ctx.fillStyle = "#525252";
                      const label = node.entity_type || "node";
                      ctx.fillText(label, node.x + r + 2, node.y + 3);
                    }
                  }}
                />
                <NodeDetailCard node={selectedNode} onClose={() => setSelectedNode(null)} />
              </>
            ) : (
              <div className="graph-minimized-hint">Graph minimized — click Expand to continue exploring.</div>
            )}
          </div>
        </section>

        <aside className="chat-pane" aria-label="Chat with graph">
          <div className="chat-pane__header">
            <h1 className="chat-pane__title">Chat with Graph</h1>
            <p className="chat-pane__subtitle">Order to Cash</p>
          </div>

          <div className="chat-scroll">
            {messages.map((msg) =>
              msg.role === "user" ? (
                <div key={msg.id} className="chat-msg chat-msg--user">
                  <div className="chat-msg__user-row">
                    <div className="chat-msg__avatar chat-msg__avatar--user" aria-hidden="true">
                      N
                    </div>
                    <span className="chat-msg__you">You</span>
                  </div>
                  <div className="chat-msg__bubble">{msg.text}</div>
                </div>
              ) : msg.greeting ? (
                <div key={msg.id} className="chat-msg chat-msg--assistant">
                  <div className="chat-msg__agent">
                    <div className="chat-msg__avatar" aria-hidden="true">
                      D
                    </div>
                    <div>
                      <div className="chat-msg__agent-name">Dodge AI</div>
                      <div className="chat-msg__agent-role">Graph Agent</div>
                    </div>
                  </div>
                  <div className="chat-msg__body chat-msg__body--assistant chat-msg__body--greeting">
                    <p className="chat-msg__text">
                      Hi! I can help you analyze the <strong>Order to Cash</strong> process.
                    </p>
                  </div>
                </div>
              ) : (
                <AssistantMessage key={msg.id} msg={msg} />
              )
            )}
          </div>

          <div className="chat-compose">
            <div className="sample-queries" aria-label="Sample questions for evaluation">
              <div className="sample-queries__label">Try a sample question</div>
              <div className="sample-queries__chips">
                {sampleQueries.map((q, idx) => (
                  <button
                    key={`${idx}-${q.slice(0, 24)}`}
                    type="button"
                    className="sample-query-chip"
                    disabled={loading}
                    title={q}
                    onClick={() => runQuery(q)}
                  >
                    {q.length > 72 ? `${q.slice(0, 69)}…` : q}
                  </button>
                ))}
              </div>
            </div>
            <div className="chat-status">
              <span className={`chat-status__dot ${loading ? "chat-status__dot--busy" : ""}`} aria-hidden="true" />
              {loading ? "Dodge AI is working on your request…" : "Dodge AI is awaiting instructions"}
            </div>
            <div className="chat-input-shell">
              <textarea
                className="chat-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Analyze anything"
                rows={3}
                disabled={loading}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendQuery();
                  }
                }}
              />
              <button type="button" className="chat-send" disabled={loading || !input.trim()} onClick={sendQuery}>
                Send
              </button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
