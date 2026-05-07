import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

  useEffect(() => {
    if (token) localStorage.setItem("dbops_token", token);
    else localStorage.removeItem("dbops_token");
  }, [token]);

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

  return (
    <main style={{ fontFamily: "Arial, sans-serif", maxWidth: 900, margin: "24px auto", padding: "0 16px" }}>
      <h1>DBOps Control Center</h1>
      <p>Render-first database operations dashboard (JWT, RBAC, whitelisted SQL reports).</p>

      {!token ? (
        <section style={{ marginBottom: 24, border: "1px solid #ddd", padding: 16, borderRadius: 8 }}>
          <h2>Sign in</h2>
          {authError ? <p style={{ color: "#b00020" }}>{authError}</p> : null}
          <form onSubmit={login} style={{ display: "grid", gap: 8, maxWidth: 360 }}>
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
            <button type="submit">Login</button>
          </form>

          <h3 style={{ marginTop: 24 }}>First-time setup (bootstrap DBA)</h3>
          <p style={{ color: "#555", fontSize: 14 }}>
            Use once when the database has no users. Role must be DBA (fixed below).
          </p>
          <form onSubmit={bootstrapRegister} style={{ display: "grid", gap: 8, maxWidth: 360 }}>
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
            <button type="submit">Create first DBA</button>
          </form>
        </section>
      ) : (
        <section style={{ marginBottom: 24, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <span>
            Signed in as <strong>{me?.email}</strong> ({me?.role})
          </span>
          <button type="button" onClick={logout}>
            Log out
          </button>
        </section>
      )}

      {token && canManageUsers ? (
        <section style={{ marginBottom: 24, border: "1px solid #ddd", padding: 16, borderRadius: 8 }}>
          <h2>Create user (DBA)</h2>
          <form onSubmit={createUser} style={{ display: "grid", gap: 8, maxWidth: 360 }}>
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
            <button type="submit">Create user</button>
          </form>
        </section>
      ) : null}

      {token ? (
        <>
          <section style={{ marginBottom: 24 }}>
            <h2>Operational Summary</h2>
            {summary ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
                <Card label="Total" value={summary.total_incidents} />
                <Card label="Open" value={summary.open_incidents} />
                <Card label="Resolved" value={summary.resolved_incidents} />
                <Card label="High Severity" value={summary.high_severity_incidents} />
              </div>
            ) : (
              <p>Loading summary...</p>
            )}
          </section>

          <section style={{ marginBottom: 24, border: "1px solid #ddd", padding: 16, borderRadius: 8 }}>
            <h2>SQL reports (read-only)</h2>
            <p style={{ color: "#555", fontSize: 14 }}>
              Pre-approved SELECT queries with bound parameters. Executions are audited (DBA can view history).
            </p>
            {reportCatalog.length === 0 ? (
              <p>Loading catalog...</p>
            ) : (
              <form onSubmit={runReport} style={{ display: "grid", gap: 12 }}>
                <label style={{ display: "grid", gap: 4 }}>
                  <span>Report</span>
                  <select value={selectedReportKey} onChange={(e) => setSelectedReportKey(e.target.value)}>
                    {reportCatalog.map((r) => (
                      <option key={r.key} value={r.key}>
                        {r.title}
                      </option>
                    ))}
                  </select>
                </label>
                {reportCatalog.find((r) => r.key === selectedReportKey)?.description ? (
                  <p style={{ margin: 0, color: "#555", fontSize: 14 }}>
                    {reportCatalog.find((r) => r.key === selectedReportKey).description}
                  </p>
                ) : null}
                {(reportCatalog.find((r) => r.key === selectedReportKey)?.params || []).map((p) => (
                  <label key={p.name} style={{ display: "grid", gap: 4 }}>
                    <span>
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
                {reportError ? <p style={{ color: "#b00020", margin: 0 }}>{reportError}</p> : null}
                <button type="submit">Run report</button>
              </form>
            )}
            {reportResult ? (
              <div style={{ marginTop: 16 }}>
                <p style={{ margin: "0 0 8px", fontSize: 14, color: "#555" }}>
                  {reportResult.row_count} row(s) in {reportResult.duration_ms} ms
                  {reportResult.truncated ? " (truncated to 500 rows)" : ""}
                </p>
                <div style={{ overflowX: "auto" }}>
                  <table cellPadding="8" style={{ borderCollapse: "collapse", minWidth: "100%" }}>
                    <thead>
                      <tr>
                        {(reportResult.columns || []).map((col) => (
                          <th key={col} align="left" style={{ borderBottom: "1px solid #ccc" }}>
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(reportResult.rows || []).map((row, idx) => (
                        <tr key={idx} style={{ borderTop: "1px solid #eee" }}>
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
            <section style={{ marginBottom: 24, border: "1px solid #ddd", padding: 16, borderRadius: 8 }}>
              <h2>Report audit trail (DBA)</h2>
              <p style={{ color: "#555", fontSize: 14 }}>Recent whitelisted report executions.</p>
              {reportRuns.length === 0 ? (
                <p>No executions logged yet.</p>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table cellPadding="8" style={{ borderCollapse: "collapse", width: "100%" }}>
                    <thead>
                      <tr>
                        <th align="left">Time</th>
                        <th align="left">User</th>
                        <th align="left">Report</th>
                        <th align="left">Rows</th>
                        <th align="left">ms</th>
                        <th align="left">OK</th>
                        <th align="left">Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportRuns.map((run) => (
                        <tr key={run.id} style={{ borderTop: "1px solid #ddd" }}>
                          <td style={{ fontSize: 13 }}>{run.created_at}</td>
                          <td>{run.user_email}</td>
                          <td>{run.report_key}</td>
                          <td>{run.row_count ?? "—"}</td>
                          <td>{run.duration_ms ?? "—"}</td>
                          <td>{run.success ? "yes" : "no"}</td>
                          <td style={{ fontSize: 12, maxWidth: 220 }} title={run.error_message || ""}>
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
            <section style={{ marginBottom: 24 }}>
              <h2>Create Incident</h2>
              <form onSubmit={createIncident} style={{ display: "grid", gap: 8 }}>
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
                <button type="submit">Create</button>
              </form>
            </section>
          ) : (
            <p style={{ color: "#555" }}>
              Your role (Viewer) can list incidents, use the summary, and run predefined read-only SQL reports.
            </p>
          )}

          <section>
            <h2>Incidents</h2>
            {incidents.length === 0 ? (
              <p>No incidents yet.</p>
            ) : (
              <table width="100%" cellPadding="8" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th align="left">Title</th>
                    <th align="left">Severity</th>
                    <th align="left">Owner</th>
                    <th align="left">Status</th>
                    <th align="left">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map((incident) => (
                    <tr key={incident.id} style={{ borderTop: "1px solid #ddd" }}>
                      <td>{incident.title}</td>
                      <td>{incident.severity}</td>
                      <td>{incident.owner}</td>
                      <td>{incident.status}</td>
                      <td>
                        {incident.status === "open" && canResolve ? (
                          <button type="button" onClick={() => resolveIncident(incident.id)}>
                            Resolve
                          </button>
                        ) : incident.status === "open" ? (
                          <span style={{ color: "#777" }}>DBA only</span>
                        ) : (
                          "Closed"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      ) : null}
    </main>
  );
}

function Card({ label, value }) {
  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12 }}>
      <div style={{ color: "#555", fontSize: 14 }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700 }}>{value}</div>
    </div>
  );
}
