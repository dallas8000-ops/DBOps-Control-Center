import { useEffect, useState } from "react";

const API_URL = String(import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

function headers(token, json = true) {
  const h = {};
  if (json) h["Content-Type"] = "application/json";
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("dbops_token") || "");
  const [me, setMe] = useState(null);
  const [authError, setAuthError] = useState("");
  const [incidents, setIncidents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [bootstrapForm, setBootstrapForm] = useState({
    email: "",
    password: "",
    confirm: "",
  });
  const [userForm, setUserForm] = useState({
    email: "",
    password: "",
    role: "Viewer",
  });
  const [form, setForm] = useState({
    title: "",
    description: "",
    severity: "medium",
    owner: "unassigned",
  });
  const [reportCatalog, setReportCatalog] = useState([]);
  const [selectedReportKey, setSelectedReportKey] = useState("");
  const [reportParams, setReportParams] = useState({});
  const [reportResult, setReportResult] = useState(null);
  const [reportRuns, setReportRuns] = useState([]);
  const [reportError, setReportError] = useState("");
  const [connectionHealth, setConnectionHealth] = useState({ kind: "loading" });

  useEffect(() => {
    if (token) localStorage.setItem("dbops_token", token);
    else localStorage.removeItem("dbops_token");
  }, [token]);

  useEffect(() => {
    let cancelled = false;
    async function ping(showSpinner) {
      if (showSpinner) setConnectionHealth({ kind: "loading" });
      try {
        const res = await fetch(`${API_URL}/health`);
        const body = await res.json().catch(() => ({}));
        if (cancelled) return;
        if (res.ok && body.database === "reachable") {
          setConnectionHealth({ kind: "ok" });
          return;
        }
        if (res.status === 503 && body.database === "unreachable") {
          setConnectionHealth({ kind: "db_unreachable" });
          return;
        }
        setConnectionHealth({ kind: "api_error", status: res.status });
      } catch {
        if (!cancelled) setConnectionHealth({ kind: "network" });
      }
    }
    ping(true);
    const interval = setInterval(() => ping(false), 60_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  async function loadMe() {
    if (!token) {
      setMe(null);
      return;
    }
    const res = await fetch(`${API_URL}/auth/me`, { headers: headers(token, false) });
    if (!res.ok) {
      setToken("");
      setMe(null);
      return;
    }
    setMe(await res.json());
  }

  async function loadData() {
    if (!token) {
      setIncidents([]);
      setSummary(null);
      return;
    }
    const [incidentsRes, summaryRes] = await Promise.all([
      fetch(`${API_URL}/incidents`, { headers: headers(token, false) }),
      fetch(`${API_URL}/reports/summary`, { headers: headers(token, false) }),
    ]);
    if (incidentsRes.status === 401 || summaryRes.status === 401) {
      setToken("");
      setMe(null);
      return;
    }
    setIncidents(await incidentsRes.json());
    setSummary(await summaryRes.json());
  }

  async function loadReportCatalog() {
    if (!token) {
      setReportCatalog([]);
      setSelectedReportKey("");
      setReportResult(null);
      setReportError("");
      return;
    }
    const res = await fetch(`${API_URL}/reports/catalog`, { headers: headers(token, false) });
    if (res.status === 401) {
      setToken("");
      setMe(null);
      return;
    }
    const data = await res.json();
    setReportCatalog(data);
  }

  async function loadReportRuns() {
    if (!token || me?.role !== "DBA") {
      setReportRuns([]);
      return;
    }
    const res = await fetch(`${API_URL}/reports/runs?limit=50`, { headers: headers(token, false) });
    if (!res.ok) return;
    setReportRuns(await res.json());
  }

  useEffect(() => {
    loadMe();
  }, [token]);

  useEffect(() => {
    loadData();
  }, [token, me]);

  useEffect(() => {
    loadReportCatalog();
  }, [token]);

  useEffect(() => {
    loadReportRuns();
  }, [token, me]);

  useEffect(() => {
    if (!reportCatalog.length) {
      setSelectedReportKey("");
      return;
    }
    setSelectedReportKey((prev) =>
      prev && reportCatalog.some((r) => r.key === prev) ? prev : reportCatalog[0].key
    );
  }, [reportCatalog]);

  useEffect(() => {
    if (!selectedReportKey || !reportCatalog.length) {
      setReportParams({});
      return;
    }
    const spec = reportCatalog.find((r) => r.key === selectedReportKey);
    if (!spec) return;
    const next = {};
    for (const p of spec.params) {
      if (p.default !== undefined && p.default !== null) {
        next[p.name] = p.default;
      } else {
        next[p.name] = p.type === "int" ? 0 : "";
      }
    }
    setReportParams(next);
    setReportResult(null);
    setReportError("");
  }, [selectedReportKey, reportCatalog]);

  async function login(e) {
    e.preventDefault();
    setAuthError("");
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: headers("", true),
      body: JSON.stringify(loginForm),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setAuthError(body.detail || "Login failed");
      return;
    }
    const data = await res.json();
    setToken(data.access_token);
    setLoginForm({ email: "", password: "" });
  }

  async function bootstrapRegister(e) {
    e.preventDefault();
    setAuthError("");
    if (bootstrapForm.password !== bootstrapForm.confirm) {
      setAuthError("Passwords do not match");
      return;
    }
    const res = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: bootstrapForm.email,
        password: bootstrapForm.password,
        role: "DBA",
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setAuthError(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail) || "Registration failed");
      return;
    }
    setBootstrapForm({ email: "", password: "", confirm: "" });
    setAuthError("");
    alert("Admin created. Sign in below.");
  }

  async function createUser(e) {
    e.preventDefault();
    setAuthError("");
    const res = await fetch(`${API_URL}/auth/users`, {
      method: "POST",
      headers: headers(token, true),
      body: JSON.stringify({
        email: userForm.email,
        password: userForm.password,
        role: userForm.role,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setAuthError(body.detail || "Create user failed");
      return;
    }
    setUserForm({ email: "", password: "", role: "Viewer" });
  }

  function logout() {
    setToken("");
    setMe(null);
    setIncidents([]);
    setSummary(null);
    setReportCatalog([]);
    setSelectedReportKey("");
    setReportParams({});
    setReportResult(null);
    setReportRuns([]);
    setReportError("");
  }

  async function runReport(e) {
    e.preventDefault();
    setReportError("");
    const spec = reportCatalog.find((r) => r.key === selectedReportKey);
    const paramsPayload = {};
    if (spec) {
      for (const p of spec.params) {
        const raw = reportParams[p.name];
        if (p.type === "int") {
          paramsPayload[p.name] = Number.parseInt(String(raw), 10);
        } else {
          paramsPayload[p.name] = raw;
        }
      }
    }
    const res = await fetch(`${API_URL}/reports/run`, {
      method: "POST",
      headers: headers(token, true),
      body: JSON.stringify({ report_key: selectedReportKey, params: paramsPayload }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      setReportResult(null);
      setReportError(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail) || "Report failed");
      return;
    }
    setReportResult(body);
    if (me?.role === "DBA") {
      loadReportRuns();
    }
  }

  async function createIncident(e) {
    e.preventDefault();
    await fetch(`${API_URL}/incidents`, {
      method: "POST",
      headers: headers(token, true),
      body: JSON.stringify(form),
    });
    setForm({
      title: "",
      description: "",
      severity: "medium",
      owner: "unassigned",
    });
    await loadData();
  }

  async function resolveIncident(id) {
    await fetch(`${API_URL}/incidents/${id}/resolve`, {
      method: "PATCH",
      headers: headers(token, false),
    });
    await loadData();
  }

  const role = me?.role;
  const canCreateIncident = role === "DBA" || role === "Analyst";
  const canResolve = role === "DBA";
  const canManageUsers = role === "DBA";
  const selectedReport = reportCatalog.find((r) => r.key === selectedReportKey);

  return (
    <main className="app-shell">
      <header className="page-header">
        <h1 className="page-title">DBOps Control Center</h1>
        <p className="page-lede">
          Render-first database operations dashboard (JWT, RBAC, whitelisted SQL reports).
        </p>
      </header>

      {!token ? (
        <section className="panel">
          {connectionHealth.kind === "loading" ? (
            <div className="health-strip health-strip--loading" role="status">
              <strong>System status:</strong> Checking API and PostgreSQL…
            </div>
          ) : null}
          {connectionHealth.kind === "ok" ? (
            <div className="health-strip health-strip--ok" role="status">
              <strong>System status:</strong> API reachable · PostgreSQL reachable. Schema updates run automatically when the API
              starts (Alembic).
            </div>
          ) : null}
          {connectionHealth.kind === "db_unreachable" ? (
            <div className="health-strip health-strip--warn" role="alert">
              <strong>Database:</strong> API is up but PostgreSQL is not reachable from the server. On Render, verify the API service
              has <code className="pill-muted">DATABASE_URL</code> and try appending <code className="pill-muted">?sslmode=require</code>{" "}
              if SSL is required.
            </div>
          ) : null}
          {connectionHealth.kind === "network" ? (
            <div className="health-strip health-strip--bad" role="alert">
              <strong>API:</strong> Cannot reach <code className="pill-muted">{API_URL}</code>. Confirm{" "}
              <code className="pill-muted">VITE_API_URL</code> on the static site matches your deployed API URL, then redeploy the
              frontend.
            </div>
          ) : null}
          {connectionHealth.kind === "api_error" ? (
            <div className="health-strip health-strip--bad" role="alert">
              <strong>API:</strong> Unexpected response ({connectionHealth.status}). Check API logs on Render.
            </div>
          ) : null}

          <h2 className="panel-title">Sign in</h2>
          {authError ? <p className="error-text">{authError}</p> : null}
          <form className="form-grid form-grid--narrow" onSubmit={login}>
            <input
              type="email"
              required
              placeholder="Email"
              value={loginForm.email}
              onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
            />
            <input
              type="password"
              required
              placeholder="Password"
              value={loginForm.password}
              onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
            />
            <button type="submit" className="btn btn-primary">
              Login
            </button>
          </form>

          <h3 className="section-lede">First-time setup (bootstrap DBA)</h3>
          <p className="panel-sub">Use once when the database has no users. Role must be DBA (fixed below).</p>
          <form className="form-grid form-grid--narrow" onSubmit={bootstrapRegister}>
            <input
              type="email"
              required
              placeholder="Admin email"
              value={bootstrapForm.email}
              onChange={(e) => setBootstrapForm({ ...bootstrapForm, email: e.target.value })}
            />
            <input
              type="password"
              required
              minLength={8}
              placeholder="Password (min 8 characters)"
              value={bootstrapForm.password}
              onChange={(e) => setBootstrapForm({ ...bootstrapForm, password: e.target.value })}
            />
            <input
              type="password"
              required
              placeholder="Confirm password"
              value={bootstrapForm.confirm}
              onChange={(e) => setBootstrapForm({ ...bootstrapForm, confirm: e.target.value })}
            />
            <button type="submit" className="btn btn-primary">
              Create first DBA
            </button>
          </form>
        </section>
      ) : (
        <div className="top-bar panel">
          <span className="top-bar-meta">
            Signed in as <strong>{me?.email}</strong> ({me?.role})
          </span>
          <button type="button" className="btn btn-ghost" onClick={logout}>
            Log out
          </button>
        </div>
      )}

      {token && canManageUsers ? (
        <section className="panel">
          <h2 className="panel-title">Create user (DBA)</h2>
          <form className="form-grid form-grid--narrow" onSubmit={createUser}>
            <input
              type="email"
              required
              placeholder="Email"
              value={userForm.email}
              onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
            />
            <input
              type="password"
              required
              minLength={8}
              placeholder="Password"
              value={userForm.password}
              onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
            />
            <select value={userForm.role} onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}>
              <option value="Viewer">Viewer</option>
              <option value="Analyst">Analyst</option>
              <option value="DBA">DBA</option>
            </select>
            <button type="submit" className="btn btn-primary">
              Create user
            </button>
          </form>
        </section>
      ) : null}

      {token ? (
        <>
          <section className="stack-gap">
            <h2 className="panel-title">Operational Summary</h2>
            {summary ? (
              <div className="summary-grid">
                <Card label="Total" value={summary.total_incidents} />
                <Card label="Open" value={summary.open_incidents} />
                <Card label="Resolved" value={summary.resolved_incidents} />
                <Card label="High Severity" value={summary.high_severity_incidents} />
              </div>
            ) : (
              <p className="empty-state">Loading summary...</p>
            )}
          </section>

          <section className="panel">
            <h2 className="panel-title">SQL reports (read-only)</h2>
            <p className="panel-sub">
              Pre-approved SELECT queries with bound parameters. Executions are audited (DBA can view history).
            </p>
            {reportCatalog.length === 0 ? (
              <p className="empty-state">Loading catalog...</p>
            ) : (
              <form className="form-grid" onSubmit={runReport}>
                <label className="field">
                  <span className="field-label">Report</span>
                  <select value={selectedReportKey} onChange={(e) => setSelectedReportKey(e.target.value)}>
                    {reportCatalog.map((r) => (
                      <option key={r.key} value={r.key}>
                        {r.title}
                      </option>
                    ))}
                  </select>
                </label>
                {selectedReport?.description ? <p className="hint">{selectedReport.description}</p> : null}
                {(selectedReport?.params || []).map((p) => (
                  <label key={p.name} className="field">
                    <span className="field-label">
                      {p.name}
                      {p.min != null || p.max != null ? ` (${p.min ?? "?"}–${p.max ?? "?"})` : ""}
                    </span>
                    <input
                      type="number"
                      value={reportParams[p.name] ?? ""}
                      onChange={(e) =>
                        setReportParams({
                          ...reportParams,
                          [p.name]: e.target.value === "" ? "" : Number(e.target.value),
                        })
                      }
                      min={p.min ?? undefined}
                      max={p.max ?? undefined}
                    />
                  </label>
                ))}
                {reportError ? <p className="error-text">{reportError}</p> : null}
                <button type="submit" className="btn btn-primary">
                  Run report
                </button>
              </form>
            )}
            {reportResult ? (
              <div className="stack-gap">
                <p className="report-meta">
                  {reportResult.row_count} row(s) in {reportResult.duration_ms} ms
                  {reportResult.truncated ? " (truncated to 500 rows)" : ""}
                </p>
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        {(reportResult.columns || []).map((col) => (
                          <th key={col}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(reportResult.rows || []).map((row, idx) => (
                        <tr key={idx}>
                          {(reportResult.columns || []).map((col) => (
                            <td key={col}>{row[col] == null ? "" : String(row[col])}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </section>

          {canManageUsers ? (
            <section className="panel">
              <h2 className="panel-title">Report audit trail (DBA)</h2>
              <p className="panel-sub">Recent whitelisted report executions.</p>
              {reportRuns.length === 0 ? (
                <p className="empty-state">No executions logged yet.</p>
              ) : (
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>User</th>
                        <th>Report</th>
                        <th>Rows</th>
                        <th>ms</th>
                        <th>OK</th>
                        <th>Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportRuns.map((run) => (
                        <tr key={run.id}>
                          <td className="hint">{run.created_at}</td>
                          <td>{run.user_email}</td>
                          <td>{run.report_key}</td>
                          <td>{run.row_count ?? "—"}</td>
                          <td>{run.duration_ms ?? "—"}</td>
                          <td>{run.success ? "yes" : "no"}</td>
                          <td className="hint" title={run.error_message || ""}>
                            {run.error_message
                              ? run.error_message.length > 80
                                ? `${run.error_message.slice(0, 80)}…`
                                : run.error_message
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          ) : null}

          {canCreateIncident ? (
            <section className="panel">
              <h2 className="panel-title">Create Incident</h2>
              <form className="form-grid" onSubmit={createIncident}>
                <input
                  required
                  placeholder="Title"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
                <textarea
                  required
                  placeholder="Description"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
                <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
                <input
                  placeholder="Owner"
                  value={form.owner}
                  onChange={(e) => setForm({ ...form, owner: e.target.value })}
                />
                <button type="submit" className="btn btn-primary">
                  Create
                </button>
              </form>
            </section>
          ) : (
            <p className="hint stack-gap">
              Your role (Viewer) can list incidents, use the summary, and run predefined read-only SQL reports.
            </p>
          )}

          <section className="stack-gap">
            <h2 className="panel-title">Incidents</h2>
            {incidents.length === 0 ? (
              <p className="empty-state">No incidents yet.</p>
            ) : (
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Title</th>
                      <th>Severity</th>
                      <th>Owner</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {incidents.map((incident) => (
                      <tr key={incident.id}>
                        <td>{incident.title}</td>
                        <td>{incident.severity}</td>
                        <td>{incident.owner}</td>
                        <td>{incident.status}</td>
                        <td>
                          {incident.status === "open" && canResolve ? (
                            <button type="button" className="btn btn-primary" onClick={() => resolveIncident(incident.id)}>
                              Resolve
                            </button>
                          ) : incident.status === "open" ? (
                            <span className="pill-muted">DBA only</span>
                          ) : (
                            "Closed"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : null}
    </main>
  );
}

function Card({ label, value }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
