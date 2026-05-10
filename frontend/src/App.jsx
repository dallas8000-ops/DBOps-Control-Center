import { useEffect, useState } from "react";
import PropTypes from "prop-types";

const API_URL = String(import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

const CREATE_USER_FETCH_MS = 25_000;
const REPORT_AUDIT_VIEW_LIMIT_KEY = "dbops_report_audit_view_limit";
const REPORT_AUDIT_VIEW_LIMIT_OPTIONS = new Set(["3", "10", "25", "all"]);

/** Hosted site (e.g. Render) still pointing at loopback — browser will block or fail the request. */
function apiUrlMismatchForHostedPage(apiUrl) {
  const win = globalThis.window;
  if (win === undefined) return false;
  const pageHost = win.location.hostname;
  if (pageHost === "localhost" || pageHost === "127.0.0.1") return false;
  try {
    const { hostname } = new URL(apiUrl);
    return hostname === "localhost" || hostname === "127.0.0.1";
  } catch {
    return false;
  }
}

function headers(token, json = true) {
  const h = {};
  if (json) h["Content-Type"] = "application/json";
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

/** FastAPI may return detail as string or validation array */
function formatApiDetail(body) {
  const d = body?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((item) => (typeof item === "object" && item.msg ? `${item.msg}` : JSON.stringify(item)))
      .join(" ");
  }
  if (d != null && typeof d === "object") return JSON.stringify(d);
  return "Request failed";
}

function auditErrorPreview(message) {
  if (!message) return "—";
  if (message.length <= 80) return message;
  return `${message.slice(0, 80)}…`;
}

function userAuditDetailsPreview(details) {
  if (!details || typeof details !== "object") return "—";
  const parts = Object.entries(details).map(([k, v]) => `${k}: ${String(v)}`);
  return parts.length ? parts.join(", ") : "—";
}

function reportAuditSummary(viewLimit, visibleCount, totalCount, refreshStatus) {
  let detail = "";
  if (totalCount === 0) {
    detail = "No runs loaded yet.";
  } else if (viewLimit === "all") {
    detail = `Showing all ${totalCount} run(s).`;
  } else {
    const requested = Number.parseInt(viewLimit, 10);
    if (Number.isNaN(requested)) {
      detail = `Showing ${visibleCount} of ${totalCount} run(s).`;
    } else if (totalCount <= requested) {
      detail = `Showing all ${totalCount} available run(s).`;
    } else {
      detail = `Showing the latest ${visibleCount} of ${totalCount} run(s).`;
    }
  }

  if (!refreshStatus) return detail;
  return `${refreshStatus} ${detail}`.trim();
}

/** Stable React key for JSON-serializable report rows from the API */
function reportRowKey(row) {
  return JSON.stringify(row);
}

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function sessionErrorMessage(detailText = "") {
  const detail = String(detailText || "").toLowerCase();
  if (detail.includes("disabled")) return "Your account is disabled. Contact a DBA.";
  if (detail.includes("expired") || detail.includes("invalid")) return "Your session expired. Please sign in again.";
  return "Your session is no longer valid. Please sign in again.";
}

function authErrorMessage(status, body, fallback) {
  const detail = formatApiDetail(body);
  const detailLower = detail.toLowerCase();

  if (detailLower.includes("disabled")) return "Your account is disabled. Contact a DBA.";
  if (status === 429) return "Too many auth requests. Please try again shortly.";
  if (status === 401) return "Incorrect email or password.";
  if (status === 403 && detailLower.includes("bootstrap complete")) {
    return "Setup is already complete. Sign in with an existing DBA account.";
  }
  if (status === 409 && detailLower.includes("already registered")) {
    return "That email is already registered.";
  }
  return detail && detail !== "Request failed" ? detail : fallback;
}

async function parseResponseBody(res) {
  return res.json().catch(() => ({}));
}

function toIncidentQuery(filters) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.owner) params.set("owner", filters.owner);
  if (filters.search) params.set("search", filters.search);
  if (filters.startDate) params.set("start_date", filters.startDate);
  if (filters.endDate) params.set("end_date", filters.endDate);
  if (filters.sort) params.set("sort", filters.sort);
  const query = params.toString();
  return query ? `?${query}` : "";
}

function reportParamsPayload(spec, reportParams) {
  const paramsPayload = {};
  if (!spec) return paramsPayload;
  for (const p of spec.params) {
    const raw = reportParams[p.name];
    if (p.type === "int") {
      paramsPayload[p.name] = Number.parseInt(String(raw), 10);
    } else {
      paramsPayload[p.name] = raw;
    }
  }
  return paramsPayload;
}

function csvFilenameFromContentDisposition(contentDisposition, fallbackReportKey) {
  const fallback = `${fallbackReportKey}.csv`;
  if (!contentDisposition) return fallback;

  const sanitizeFilename = (value) => value.replaceAll("/", "_").replaceAll("\\", "_");

  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(contentDisposition);
  if (utf8Match?.[1]) {
    try {
      return sanitizeFilename(decodeURIComponent(utf8Match[1]));
    } catch {
      return sanitizeFilename(utf8Match[1]);
    }
  }

  const quotedMatch = /filename="([^"]+)"/i.exec(contentDisposition);
  if (quotedMatch?.[1]) return sanitizeFilename(quotedMatch[1]);

  const bareMatch = /filename=([^;]+)/i.exec(contentDisposition);
  if (bareMatch?.[1]) return sanitizeFilename(bareMatch[1].trim());

  return fallback;
}

function utcWallClockToLocalPreview(hourUtc, minuteUtc) {
  const safeHour = Number.isFinite(hourUtc) ? hourUtc : 0;
  const safeMinute = Number.isFinite(minuteUtc) ? minuteUtc : 0;
  const fixedUtc = new Date(Date.UTC(2030, 0, 1, safeHour, safeMinute, 0));
  return fixedUtc.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

function formatUtcIsoAsLocal(isoValue) {
  if (!isoValue) return "—";
  const date = new Date(isoValue);
  if (Number.isNaN(date.getTime())) return isoValue;
  return date.toLocaleString([], {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  });
}

function formatSchedulerStamp(isoValue) {
  if (!isoValue) return "—";
  const value = new Date(isoValue);
  if (Number.isNaN(value.getTime())) return isoValue;
  return value.toLocaleString([], {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    month: "2-digit",
    day: "2-digit",
    timeZoneName: "short",
  });
}

function formatCurrencyFromCents(cents) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format((Number(cents) || 0) / 100);
}

function HealthConnectionMessages({ health, apiUrl }) {
  switch (health.kind) {
    case "loading":
      return (
        <output className="health-strip health-strip--loading">
          <strong>System status:</strong> Checking API and PostgreSQL…
        </output>
      );
    case "ok":
      return (
        <output className="health-strip health-strip--ok">
          <strong>System status:</strong> API reachable · PostgreSQL reachable. Schema updates run automatically when the API
          starts (Alembic).
        </output>
      );
    case "db_unreachable":
      return (
        <div className="health-strip health-strip--warn" role="alert">
          <strong>Database:</strong> API is up but PostgreSQL is not reachable from the server. On Render, verify the API service
          has <code className="pill-muted">DATABASE_URL</code> and try appending <code className="pill-muted">?sslmode=require</code>{" "}
          if SSL is required.
        </div>
      );
    case "network":
      return (
        <div className="health-strip health-strip--bad" role="alert">
          <strong>API:</strong> Cannot reach <code className="pill-muted">{apiUrl}</code>. Confirm{" "}
          <code className="pill-muted">VITE_API_URL</code> on the static site matches your deployed API URL, then redeploy the
          frontend.
        </div>
      );
    case "api_error":
      return (
        <div className="health-strip health-strip--bad" role="alert">
          <strong>API:</strong> Unexpected response ({health.status}). Check API logs on Render.
        </div>
      );
    default:
      return null;
  }
}

HealthConnectionMessages.propTypes = {
  health: PropTypes.object.isRequired,
  apiUrl: PropTypes.string.isRequired,
};

function LoginPanel({
  connectionHealth,
  apiUrl,
  authError,
  loginForm,
  setLoginForm,
  onLogin,
  bootstrapForm,
  setBootstrapForm,
  onBootstrap,
}) {
  return (
    <section className="panel">
      <HealthConnectionMessages health={connectionHealth} apiUrl={apiUrl} />

      <h2 className="panel-title">Sign in</h2>
      {authError ? <p className="error-text">{authError}</p> : null}
      <form className="form-grid form-grid--narrow" onSubmit={onLogin}>
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
      <form className="form-grid form-grid--narrow" onSubmit={onBootstrap}>
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
  );
}

LoginPanel.propTypes = {
  connectionHealth: PropTypes.object.isRequired,
  apiUrl: PropTypes.string.isRequired,
  authError: PropTypes.string.isRequired,
  loginForm: PropTypes.shape({ email: PropTypes.string, password: PropTypes.string }).isRequired,
  setLoginForm: PropTypes.func.isRequired,
  onLogin: PropTypes.func.isRequired,
  bootstrapForm: PropTypes.shape({
    email: PropTypes.string,
    password: PropTypes.string,
    confirm: PropTypes.string,
  }).isRequired,
  setBootstrapForm: PropTypes.func.isRequired,
  onBootstrap: PropTypes.func.isRequired,
};

function IncidentResolveCell({ incident, canResolve, onResolve }) {
  if (incident.status === "open" && canResolve) {
    return (
      <button type="button" className="btn btn-primary" onClick={() => onResolve(incident.id)}>
        Resolve
      </button>
    );
  }
  if (incident.status === "open") {
    return <span className="pill-muted">DBA only</span>;
  }
  return "Closed";
}

IncidentResolveCell.propTypes = {
  incident: PropTypes.shape({
    id: PropTypes.number.isRequired,
    status: PropTypes.string.isRequired,
  }).isRequired,
  canResolve: PropTypes.bool.isRequired,
  onResolve: PropTypes.func.isRequired,
};

function Card({ label, value }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

Card.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
};

function PlanUsageBanner({ billing, planUsage, kind }) {
  if (!billing || !planUsage) return null;

  const isUserKind = kind === "users";
  const used = isUserKind ? planUsage.user_slots_used : planUsage.schedule_slots_used;
  const remaining = isUserKind ? planUsage.user_slots_remaining : planUsage.schedule_slots_remaining;
  const atLimit = isUserKind ? planUsage.users_at_limit : planUsage.schedules_at_limit;
  const limit = isUserKind ? billing.max_users : billing.max_schedules;
  const noun = isUserKind ? "user seats" : "schedules";
  const klass = atLimit ? "health-strip health-strip--warn" : "health-strip health-strip--ok";

  return (
    <div className={klass}>
      <strong>{billing.plan_key}</strong> · {billing.billing_status} · {used}/{limit} {noun} used · {remaining} remaining
      {atLimit ? ` · Limit reached for ${noun}` : ""}
    </div>
  );
}

PlanUsageBanner.propTypes = {
  billing: PropTypes.shape({
    plan_key: PropTypes.string.isRequired,
    billing_status: PropTypes.string.isRequired,
    max_users: PropTypes.number,
    max_schedules: PropTypes.number,
  }),
  planUsage: PropTypes.shape({
    user_slots_used: PropTypes.number.isRequired,
    user_slots_remaining: PropTypes.number.isRequired,
    users_at_limit: PropTypes.bool.isRequired,
    schedule_slots_used: PropTypes.number.isRequired,
    schedule_slots_remaining: PropTypes.number.isRequired,
    schedules_at_limit: PropTypes.bool.isRequired,
  }),
  kind: PropTypes.oneOf(["users", "schedules"]).isRequired,
};

function ActivityTrendChart({ points }) {
  if (!points || points.length === 0) {
    return <p className="empty-state">Activity trend will appear once live usage starts accumulating.</p>;
  }

  const maxValue = Math.max(
    1,
    ...points.flatMap((point) => [point.incidents_created, point.report_runs, point.schedules_created]),
  );

  return (
    <div className="activity-trend">
      {points.map((point) => (
        <div key={point.day} className="activity-trend__day">
          <div className="activity-trend__bars" aria-label={`${point.label}: ${point.report_runs} runs, ${point.incidents_created} incidents, ${point.schedules_created} schedules`}>
            <span className="activity-trend__bar activity-trend__bar--runs" style={{ height: `${(point.report_runs / maxValue) * 100}%` }} />
            <span className="activity-trend__bar activity-trend__bar--incidents" style={{ height: `${(point.incidents_created / maxValue) * 100}%` }} />
            <span className="activity-trend__bar activity-trend__bar--schedules" style={{ height: `${(point.schedules_created / maxValue) * 100}%` }} />
          </div>
          <span className="hint activity-trend__label">{point.label}</span>
        </div>
      ))}
      <div className="activity-trend__legend hint">
        <span className="activity-trend__legend-item"><i className="activity-trend__dot activity-trend__dot--runs" /> Report runs</span>
        <span className="activity-trend__legend-item"><i className="activity-trend__dot activity-trend__dot--incidents" /> Incidents</span>
        <span className="activity-trend__legend-item"><i className="activity-trend__dot activity-trend__dot--schedules" /> Schedules</span>
      </div>
    </div>
  );
}

ActivityTrendChart.propTypes = {
  points: PropTypes.arrayOf(
    PropTypes.shape({
      day: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      incidents_created: PropTypes.number.isRequired,
      report_runs: PropTypes.number.isRequired,
      schedules_created: PropTypes.number.isRequired,
    }),
  ).isRequired,
};

function CreateUserSection({
  apiBaseUrl,
  existingUsers,
  userListLoading,
  feedback,
  userForm,
  setUserForm,
  busy,
  onSubmit,
  currentUserId,
  actionBusyId,
  onResetPassword,
  onToggleActive,
  onDeleteUser,
  userAuditLogs,
  userAuditLoading,
  billing,
  planUsage,
}) {
  const configBroken = apiUrlMismatchForHostedPage(apiBaseUrl);
  let userAuditContent = null;

  if (userAuditLoading) {
    userAuditContent = <p className="hint">Loading user admin audit…</p>;
  } else if (userAuditLogs.length === 0) {
    userAuditContent = <p className="empty-state">No user admin actions logged yet.</p>;
  } else {
    userAuditContent = (
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Target</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {userAuditLogs.map((item) => (
              <tr key={item.id}>
                <td className="hint">{item.created_at}</td>
                <td>{item.actor_email || "deleted user"}</td>
                <td>{item.action}</td>
                <td>{item.target_email}</td>
                <td className="hint">{userAuditDetailsPreview(item.details)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <section className="panel">
      <h2 className="panel-title">Create user (DBA)</h2>
      <div className="api-config-banner">
        <strong>API base URL baked into this frontend build:</strong>{" "}
        <code>{apiBaseUrl}</code>
        <span className="hint api-config-banner__note">
          On Render, set <code className="pill-muted">VITE_API_URL</code> on <strong>dbops-web</strong> to your live API (example{" "}
          <code className="pill-muted">https://dbops-api.onrender.com</code>), save, then redeploy the static site. If you only see the
          title and form with no box like this, your browser is still loading an old deploy — hard-refresh or redeploy.
        </span>
      </div>
      <p className="panel-sub">
        New accounts need a <strong>unique email</strong> (not your own). Password at least 8 characters. Roles{" "}
        <strong>Viewer</strong>, Analyst, and DBA are all allowed here.
      </p>
      <PlanUsageBanner billing={billing} planUsage={planUsage} kind="users" />
      {configBroken ? (
        <p className="error-text" role="alert">
          This page is not running on localhost, but the app is still configured to call{" "}
          <code className="pill-muted">{apiBaseUrl}</code>. Browsers will block or ignore that. In the Render dashboard, set{" "}
          <code className="pill-muted">VITE_API_URL</code> to your public API URL (for example{" "}
          <code className="pill-muted">https://dbops-api.onrender.com</code>), then redeploy <strong>dbops-web</strong>.
        </p>
      ) : null}
      <div aria-live="polite">
        {feedback.kind === "error" ? (
          <p className="error-text" role="alert">
            {feedback.text}
          </p>
        ) : null}
        {feedback.kind === "success" ? <output className="feedback-success">{feedback.text}</output> : null}
      </div>

      <h3 className="section-lede">Accounts in database</h3>
      {userListLoading ? (
        <p className="hint">Loading account list…</p>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {existingUsers.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.role}</td>
                  <td>{u.is_active ? "active" : "disabled"}</td>
                  <td>
                    <div className="action-row">
                      <button
                        type="button"
                        className="btn btn-ghost"
                        disabled={actionBusyId === u.id}
                        onClick={() => onResetPassword(u)}
                      >
                        Reset password
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        disabled={u.id === currentUserId || actionBusyId === u.id}
                        onClick={() => onToggleActive(u)}
                      >
                        {u.is_active ? "Disable" : "Enable"}
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        disabled={u.id === currentUserId || actionBusyId === u.id}
                        onClick={() => onDeleteUser(u)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="hint">
        If create fails with &quot;Email already registered&quot;, that address is already in this table (check another inbox or typo).
      </p>

      <h3 className="section-lede">User admin audit trail</h3>
      {userAuditContent}

      <form className="form-grid form-grid--narrow" onSubmit={onSubmit}>
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
        <button type="submit" className="btn btn-primary" disabled={busy || Boolean(planUsage?.users_at_limit)}>
          {busy ? "Creating…" : "Create user"}
        </button>
      </form>
      {planUsage?.users_at_limit ? <p className="error-text">Increase max users in Billing scaffold before creating another account.</p> : null}
    </section>
  );
}

function SchedulerHealthPanel({ schedulerHealth }) {
  const scheduler = schedulerHealth?.scheduler;
  if (!schedulerHealth || !scheduler) {
    return (
      <section className="panel">
        <h2 className="panel-title">Scheduler Health (DBA)</h2>
        <p className="empty-state">Loading scheduler health...</p>
      </section>
    );
  }

  const lastError = scheduler.last_iteration_error;
  const statusClass = lastError ? "health-strip health-strip--warn" : "health-strip health-strip--ok";

  return (
    <section className="panel">
      <h2 className="panel-title">Scheduler Health (DBA)</h2>
      <div className={statusClass}>
        <strong>Loop:</strong> {scheduler.loop_enabled ? "enabled" : "disabled"} · <strong>Poll:</strong>{" "}
        {scheduler.poll_seconds}s · <strong>Processed last iteration:</strong> {scheduler.last_iteration_processed}
        {lastError ? ` · Last error: ${lastError}` : " · Last iteration completed without error"}
      </div>
      <div className="summary-grid summary-grid--compact">
        <Card label="Last Start" value={formatSchedulerStamp(scheduler.last_iteration_started_at)} />
        <Card label="Last Complete" value={formatSchedulerStamp(scheduler.last_iteration_completed_at)} />
        <Card label="Consecutive Failures" value={scheduler.consecutive_failures ?? 0} />
        <Card label="Last Processed" value={scheduler.last_iteration_processed ?? 0} />
      </div>
    </section>
  );
}

SchedulerHealthPanel.propTypes = {
  schedulerHealth: PropTypes.shape({
    scheduler: PropTypes.object,
  }),
};

/* eslint-disable react/prop-types */
function SqlReportsSection({
  reportCatalog,
  selectedReportKey,
  setSelectedReportKey,
  selectedReport,
  reportParams,
  setReportParams,
  reportNotice,
  reportError,
  reportBusy,
  onRunReport,
  onExportReportCsv,
  reportResult,
}) {
  return (
    <section className="panel">
      <h2 className="panel-title">SQL reports (read-only)</h2>
      <p className="panel-sub">
        Pre-approved SELECT queries with bound parameters. Executions are audited (DBA can view history).
      </p>
      {reportCatalog.length === 0 ? (
        <p className="empty-state">Loading catalog...</p>
      ) : (
        <form className="form-grid" onSubmit={onRunReport}>
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
          {reportNotice ? <output className="feedback-success">{reportNotice}</output> : null}
          {reportError ? <p className="error-text">{reportError}</p> : null}
          <div className="action-row">
            <button type="submit" className="btn btn-primary" disabled={reportBusy}>
              {reportBusy ? "Working..." : "Run report"}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={!reportResult || reportBusy}
              onClick={onExportReportCsv}
            >
              Export CSV
            </button>
          </div>
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
                {(reportResult.rows || []).map((row) => (
                  <tr key={reportRowKey(row)}>
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
  );
}

SqlReportsSection.propTypes = {
  reportCatalog: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
    }),
  ).isRequired,
  selectedReportKey: PropTypes.string.isRequired,
  setSelectedReportKey: PropTypes.func.isRequired,
  selectedReport: PropTypes.shape({
    description: PropTypes.string,
    params: PropTypes.arrayOf(
      PropTypes.shape({
        name: PropTypes.string.isRequired,
        min: PropTypes.number,
        max: PropTypes.number,
      }),
    ),
  }),
  reportParams: PropTypes.object.isRequired,
  setReportParams: PropTypes.func.isRequired,
  reportNotice: PropTypes.string.isRequired,
  reportError: PropTypes.string.isRequired,
  reportBusy: PropTypes.bool.isRequired,
  onRunReport: PropTypes.func.isRequired,
  onExportReportCsv: PropTypes.func.isRequired,
  reportResult: PropTypes.shape({
    row_count: PropTypes.number.isRequired,
    duration_ms: PropTypes.number.isRequired,
    truncated: PropTypes.bool.isRequired,
    columns: PropTypes.arrayOf(PropTypes.string).isRequired,
    rows: PropTypes.arrayOf(PropTypes.object).isRequired,
  }),
};

function ScheduledReportsSection({
  reportCatalog,
  scheduleForm,
  setScheduleForm,
  scheduleLocalPreview,
  onCreateSchedule,
  scheduleBusy,
  scheduleFeedback,
  reportSchedules,
  scheduleActionBusyId,
  onToggleSchedule,
  billing,
  planUsage,
}) {
  const hasDeliveryTarget = scheduleForm.delivery_kind === "email" || scheduleForm.delivery_kind === "webhook";

  return (
    <section className="panel">
      <h2 className="panel-title">Scheduled reports (DBA)</h2>
      <p className="panel-sub">Run approved reports automatically and route completion/failure notifications.</p>
      <PlanUsageBanner billing={billing} planUsage={planUsage} kind="schedules" />

      <form className="form-grid schedule-form" onSubmit={onCreateSchedule}>
        <label className="field">
          <span className="field-label">Report</span>
          <select value={scheduleForm.report_key} onChange={(e) => setScheduleForm({ ...scheduleForm, report_key: e.target.value })}>
            {reportCatalog.map((r) => (
              <option key={r.key} value={r.key}>
                {r.title}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field-label">Cadence</span>
          <select value={scheduleForm.cadence} onChange={(e) => setScheduleForm({ ...scheduleForm, cadence: e.target.value })}>
            <option value="daily">daily</option>
            <option value="weekly">weekly</option>
          </select>
        </label>
        {scheduleForm.cadence === "weekly" ? (
          <label className="field">
            <span className="field-label">Weekday (UTC)</span>
            <select
              value={String(scheduleForm.weekday_utc)}
              onChange={(e) => setScheduleForm({ ...scheduleForm, weekday_utc: Number(e.target.value) })}
            >
              {WEEKDAY_LABELS.map((label, idx) => (
                <option key={label} value={idx}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label className="field">
          <span className="field-label">Hour (UTC)</span>
          <input
            type="number"
            min="0"
            max="23"
            value={scheduleForm.run_hour_utc}
            onChange={(e) => setScheduleForm({ ...scheduleForm, run_hour_utc: Number(e.target.value) })}
          />
        </label>
        <label className="field">
          <span className="field-label">Minute (UTC)</span>
          <input
            type="number"
            min="0"
            max="59"
            value={scheduleForm.run_minute_utc}
            onChange={(e) => setScheduleForm({ ...scheduleForm, run_minute_utc: Number(e.target.value) })}
          />
        </label>
        <p className="hint schedule-local-preview">
          Local time preview: {scheduleLocalPreview} (stored and executed in UTC)
        </p>
        <label className="field">
          <span className="field-label">Delivery</span>
          <select
            value={scheduleForm.delivery_kind}
            onChange={(e) => setScheduleForm({ ...scheduleForm, delivery_kind: e.target.value })}
          >
            <option value="none">none</option>
            <option value="email">email</option>
            <option value="webhook">webhook</option>
          </select>
        </label>
        {hasDeliveryTarget ? (
          <label className="field">
            <span className="field-label">Delivery target</span>
            <input
              type="text"
              required
              placeholder={scheduleForm.delivery_kind === "email" ? "ops@example.com" : "https://example.com/hook"}
              value={scheduleForm.delivery_target}
              onChange={(e) => setScheduleForm({ ...scheduleForm, delivery_target: e.target.value })}
            />
          </label>
        ) : null}
        <div className="schedule-toggle-row">
          <label className="field field--inline">
            <input
              type="checkbox"
              checked={scheduleForm.notify_on_success}
              onChange={(e) => setScheduleForm({ ...scheduleForm, notify_on_success: e.target.checked })}
            />
            <span className="field-label">Notify on success</span>
          </label>
          <label className="field field--inline">
            <input
              type="checkbox"
              checked={scheduleForm.notify_on_failure}
              onChange={(e) => setScheduleForm({ ...scheduleForm, notify_on_failure: e.target.checked })}
            />
            <span className="field-label">Notify on failure</span>
          </label>
        </div>
        <button
          type="submit"
          className="btn btn-primary schedule-submit"
          disabled={scheduleBusy || Boolean(planUsage?.schedules_at_limit)}
        >
          {scheduleBusy ? "Saving…" : "Create schedule"}
        </button>
      </form>
      {scheduleFeedback ? <p className="hint">{scheduleFeedback}</p> : null}
      {planUsage?.schedules_at_limit ? <p className="error-text">Increase max schedules in Billing scaffold before adding another schedule.</p> : null}

      {reportSchedules.length === 0 ? (
        <p className="empty-state">No schedules created yet.</p>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Report</th>
                <th>Cadence</th>
                <th>Next run</th>
                <th>Delivery</th>
                <th>Last result</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {reportSchedules.map((schedule) => (
                <tr key={schedule.id}>
                  <td>{schedule.report_key}</td>
                  <td>
                    {schedule.cadence}
                    {schedule.cadence === "weekly" ? ` (${WEEKDAY_LABELS[schedule.weekday_utc ?? 0]})` : ""}
                    {` @ ${String(schedule.run_hour_utc).padStart(2, "0")}:${String(schedule.run_minute_utc).padStart(2, "0")} UTC`}
                  </td>
                  <td className="hint">
                    <div>{schedule.next_run_at}</div>
                    <div className="hint">Local: {formatUtcIsoAsLocal(schedule.next_run_at)}</div>
                  </td>
                  <td>
                    {schedule.delivery_kind}
                    {schedule.delivery_target ? `: ${schedule.delivery_target}` : ""}
                  </td>
                  <td className="hint">{schedule.last_error || (schedule.last_success_at ? "ok" : "—")}</td>
                  <td>{schedule.is_enabled ? "enabled" : "disabled"}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={scheduleActionBusyId === schedule.id}
                      onClick={() => onToggleSchedule(schedule)}
                    >
                      {schedule.is_enabled ? "Disable" : "Enable"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

ScheduledReportsSection.propTypes = {
  reportCatalog: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
    }),
  ).isRequired,
  scheduleForm: PropTypes.shape({
    report_key: PropTypes.string.isRequired,
    cadence: PropTypes.string.isRequired,
    weekday_utc: PropTypes.number,
    run_hour_utc: PropTypes.number.isRequired,
    run_minute_utc: PropTypes.number.isRequired,
    delivery_kind: PropTypes.string.isRequired,
    delivery_target: PropTypes.string.isRequired,
    notify_on_success: PropTypes.bool.isRequired,
    notify_on_failure: PropTypes.bool.isRequired,
  }).isRequired,
  setScheduleForm: PropTypes.func.isRequired,
  scheduleLocalPreview: PropTypes.string.isRequired,
  onCreateSchedule: PropTypes.func.isRequired,
  scheduleBusy: PropTypes.bool.isRequired,
  scheduleFeedback: PropTypes.string.isRequired,
  reportSchedules: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      report_key: PropTypes.string.isRequired,
      cadence: PropTypes.string.isRequired,
      weekday_utc: PropTypes.number,
      run_hour_utc: PropTypes.number.isRequired,
      run_minute_utc: PropTypes.number.isRequired,
      next_run_at: PropTypes.string,
      delivery_kind: PropTypes.string.isRequired,
      delivery_target: PropTypes.string,
      last_error: PropTypes.string,
      last_success_at: PropTypes.string,
      is_enabled: PropTypes.bool.isRequired,
    }),
  ).isRequired,
  scheduleActionBusyId: PropTypes.oneOfType([PropTypes.number, PropTypes.oneOf([null])]),
  onToggleSchedule: PropTypes.func.isRequired,
  billing: PropTypes.object,
  planUsage: PropTypes.object,
};

function ReportAuditSection({
  reportAuditViewLimit,
  setReportAuditViewLimit,
  onRefreshReportRuns,
  reportRunsLoading,
  visibleReportRuns,
  reportRuns,
  reportRunsStatus,
}) {
  return (
    <section className="panel">
      <h2 className="panel-title">Report audit trail (DBA)</h2>
      <div className="report-audit-controls">
        <label htmlFor="report-audit-view-limit"><strong>Audit view</strong></label>
        <select
          id="report-audit-view-limit"
          data-testid="report-audit-view-limit"
          value={reportAuditViewLimit}
          onChange={(e) => setReportAuditViewLimit(e.target.value)}
        >
          <option value="3">Last 3</option>
          <option value="10">Last 10</option>
          <option value="25">Last 25</option>
          <option value="all">Show all</option>
        </select>
        <button type="button" className="btn btn-ghost" onClick={onRefreshReportRuns} disabled={reportRunsLoading}>
          {reportRunsLoading ? "Refreshing…" : "Refresh"}
        </button>
        <span className="hint">
          {reportAuditSummary(reportAuditViewLimit, visibleReportRuns.length, reportRuns.length, reportRunsStatus)}
        </span>
      </div>
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
              {visibleReportRuns.map((run) => (
                <tr key={run.id}>
                  <td className="hint">{run.created_at}</td>
                  <td>{run.user_email}</td>
                  <td>{run.report_key}</td>
                  <td>{run.row_count ?? "—"}</td>
                  <td>{run.duration_ms ?? "—"}</td>
                  <td>{run.success ? "yes" : "no"}</td>
                  <td className="hint" title={run.error_message || ""}>
                    {auditErrorPreview(run.error_message)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

ReportAuditSection.propTypes = {
  reportAuditViewLimit: PropTypes.string.isRequired,
  setReportAuditViewLimit: PropTypes.func.isRequired,
  onRefreshReportRuns: PropTypes.func.isRequired,
  reportRunsLoading: PropTypes.bool.isRequired,
  visibleReportRuns: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      created_at: PropTypes.string.isRequired,
      user_email: PropTypes.string.isRequired,
      report_key: PropTypes.string.isRequired,
      row_count: PropTypes.number,
      duration_ms: PropTypes.number,
      success: PropTypes.bool.isRequired,
      error_message: PropTypes.string,
    }),
  ).isRequired,
  reportRuns: PropTypes.arrayOf(PropTypes.object).isRequired,
  reportRunsStatus: PropTypes.string.isRequired,
};

function IncidentsSection({
  incidents,
  incidentFilters,
  onIncidentFilterChange,
  onClearIncidentFilters,
  canEditIncidents,
  editingIncidentId,
  incidentEditForm,
  incidentEditError,
  onStartIncidentEdit,
  onChangeIncidentEditField,
  onSaveIncidentEdit,
  onCancelIncidentEdit,
  canResolve,
  onResolveIncident,
}) {
  function renderEditActions(incident) {
    if (!canEditIncidents) return null;
    if (editingIncidentId !== incident.id) {
      return (
        <button type="button" className="btn btn-ghost" onClick={() => onStartIncidentEdit(incident)}>
          Edit
        </button>
      );
    }
    return (
      <>
        <button type="button" className="btn btn-primary" onClick={() => onSaveIncidentEdit(incident.id)}>
          Save
        </button>
        <button type="button" className="btn btn-ghost" onClick={onCancelIncidentEdit}>
          Cancel
        </button>
      </>
    );
  }

  return (
    <section className="stack-gap">
      <h2 className="panel-title">Incidents</h2>
      <div className="incident-filters">
        <input
          type="text"
          placeholder="Search title, description, owner"
          value={incidentFilters.search}
          onChange={(e) => onIncidentFilterChange("search", e.target.value)}
        />
        <select value={incidentFilters.status} onChange={(e) => onIncidentFilterChange("status", e.target.value)}>
          <option value="">All status</option>
          <option value="open">open</option>
          <option value="resolved">resolved</option>
        </select>
        <select value={incidentFilters.severity} onChange={(e) => onIncidentFilterChange("severity", e.target.value)}>
          <option value="">All severity</option>
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
        </select>
        <input
          type="text"
          placeholder="Owner contains"
          value={incidentFilters.owner}
          onChange={(e) => onIncidentFilterChange("owner", e.target.value)}
        />
        <input
          type="date"
          value={incidentFilters.startDate}
          onChange={(e) => onIncidentFilterChange("startDate", e.target.value)}
        />
        <input
          type="date"
          value={incidentFilters.endDate}
          onChange={(e) => onIncidentFilterChange("endDate", e.target.value)}
        />
        <select value={incidentFilters.sort} onChange={(e) => onIncidentFilterChange("sort", e.target.value)}>
          <option value="newest">Sort: newest</option>
          <option value="oldest">Sort: oldest</option>
          <option value="severity">Sort: severity</option>
        </select>
        <button type="button" className="btn btn-ghost" onClick={onClearIncidentFilters}>
          Clear filters
        </button>
      </div>
      {incidents.length === 0 ? (
        <p className="empty-state">No incidents yet.</p>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Description</th>
                <th>Severity</th>
                <th>Owner</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((incident) => (
                <tr key={incident.id}>
                  <td>
                    {editingIncidentId === incident.id ? (
                      <input
                        className="inline-input"
                        value={incidentEditForm.title}
                        onChange={(e) => onChangeIncidentEditField("title", e.target.value)}
                      />
                    ) : (
                      incident.title
                    )}
                  </td>
                  <td>
                    {editingIncidentId === incident.id ? (
                      <input
                        className="inline-input"
                        value={incidentEditForm.description}
                        onChange={(e) => onChangeIncidentEditField("description", e.target.value)}
                      />
                    ) : (
                      incident.description
                    )}
                  </td>
                  <td>
                    {editingIncidentId === incident.id ? (
                      <select
                        className="inline-input"
                        value={incidentEditForm.severity}
                        onChange={(e) => onChangeIncidentEditField("severity", e.target.value)}
                      >
                        <option value="low">low</option>
                        <option value="medium">medium</option>
                        <option value="high">high</option>
                      </select>
                    ) : (
                      incident.severity
                    )}
                  </td>
                  <td>
                    {editingIncidentId === incident.id ? (
                      <input
                        className="inline-input"
                        value={incidentEditForm.owner}
                        onChange={(e) => onChangeIncidentEditField("owner", e.target.value)}
                      />
                    ) : (
                      incident.owner
                    )}
                  </td>
                  <td>{incident.status}</td>
                  <td>
                    <div className="action-row">
                      <IncidentResolveCell incident={incident} canResolve={canResolve} onResolve={onResolveIncident} />
                      {renderEditActions(incident)}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {incidentEditError ? <p className="error-text">{incidentEditError}</p> : null}
    </section>
  );
}

IncidentsSection.propTypes = {
  incidents: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      title: PropTypes.string.isRequired,
      description: PropTypes.string.isRequired,
      severity: PropTypes.string.isRequired,
      owner: PropTypes.string.isRequired,
      status: PropTypes.string.isRequired,
    }),
  ).isRequired,
  incidentFilters: PropTypes.shape({
    search: PropTypes.string.isRequired,
    status: PropTypes.string.isRequired,
    severity: PropTypes.string.isRequired,
    owner: PropTypes.string.isRequired,
    startDate: PropTypes.string.isRequired,
    endDate: PropTypes.string.isRequired,
    sort: PropTypes.string.isRequired,
  }).isRequired,
  onIncidentFilterChange: PropTypes.func.isRequired,
  onClearIncidentFilters: PropTypes.func.isRequired,
  canEditIncidents: PropTypes.bool.isRequired,
  editingIncidentId: PropTypes.oneOfType([PropTypes.number, PropTypes.oneOf([null])]),
  incidentEditForm: PropTypes.shape({
    title: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired,
    severity: PropTypes.string.isRequired,
    owner: PropTypes.string.isRequired,
  }).isRequired,
  incidentEditError: PropTypes.string.isRequired,
  onStartIncidentEdit: PropTypes.func.isRequired,
  onChangeIncidentEditField: PropTypes.func.isRequired,
  onSaveIncidentEdit: PropTypes.func.isRequired,
  onCancelIncidentEdit: PropTypes.func.isRequired,
  canResolve: PropTypes.bool.isRequired,
  onResolveIncident: PropTypes.func.isRequired,
};
/* eslint-enable react/prop-types */

function BusinessOpsPanel({ adminOverview, billingForm, setBillingForm, billingBusy, billingFeedback, onSaveBilling }) {
  if (!adminOverview) {
    return (
      <section className="panel">
        <h2 className="panel-title">Business Metrics (DBA)</h2>
        <p className="empty-state">Loading business metrics...</p>
      </section>
    );
  }

  const { metrics, onboarding, plan_usage: planUsage, activity_trend: activityTrend } = adminOverview;

  return (
    <section className="panel">
      <h2 className="panel-title">Business Metrics (DBA)</h2>
      <div className="summary-grid summary-grid--compact">
        <Card label="Active Users" value={`${metrics.active_users}/${metrics.total_users}`} />
        <Card label="Open Incidents" value={metrics.open_incidents} />
        <Card label="Enabled Schedules" value={metrics.enabled_schedules} />
        <Card label="Runs (24h)" value={metrics.report_runs_last_24h} />
      </div>
      <div className="summary-grid summary-grid--compact">
        <Card label="Successful Runs (24h)" value={metrics.successful_report_runs_last_24h} />
        <Card
          label="Onboarding"
          value={`${metrics.onboarding_completed_steps}/${metrics.onboarding_total_steps}`}
        />
        <Card label="Plan" value={billingForm.plan_key || "starter"} />
        <Card label="MRR Scaffold" value={formatCurrencyFromCents(billingForm.monthly_price_cents)} />
      </div>
      <div className="summary-grid summary-grid--compact">
        <Card label="User Seats Left" value={planUsage.user_slots_remaining} />
        <Card label="Schedule Slots Left" value={planUsage.schedule_slots_remaining} />
        <Card label="Billing Status" value={billingForm.billing_status} />
        <Card label="Plan Price" value={formatCurrencyFromCents(billingForm.monthly_price_cents)} />
      </div>

      <h3 className="section-lede">Billing scaffold</h3>
      <form className="form-grid schedule-form" onSubmit={onSaveBilling}>
        <label className="field">
          <span className="field-label">Plan key</span>
          <input
            type="text"
            value={billingForm.plan_key}
            onChange={(e) => setBillingForm({ ...billingForm, plan_key: e.target.value })}
          />
        </label>
        <label className="field">
          <span className="field-label">Billing status</span>
          <input
            type="text"
            value={billingForm.billing_status}
            onChange={(e) => setBillingForm({ ...billingForm, billing_status: e.target.value })}
          />
        </label>
        <label className="field">
          <span className="field-label">Monthly price (cents)</span>
          <input
            type="number"
            min="0"
            value={billingForm.monthly_price_cents}
            onChange={(e) => setBillingForm({ ...billingForm, monthly_price_cents: Number(e.target.value) })}
          />
        </label>
        <label className="field">
          <span className="field-label">Max users</span>
          <input
            type="number"
            min="1"
            value={billingForm.max_users}
            onChange={(e) => setBillingForm({ ...billingForm, max_users: Number(e.target.value) })}
          />
        </label>
        <label className="field">
          <span className="field-label">Max schedules</span>
          <input
            type="number"
            min="1"
            value={billingForm.max_schedules}
            onChange={(e) => setBillingForm({ ...billingForm, max_schedules: Number(e.target.value) })}
          />
        </label>
        <label className="field">
          <span className="field-label">Stripe customer ID</span>
          <input
            type="text"
            value={billingForm.stripe_customer_id}
            onChange={(e) => setBillingForm({ ...billingForm, stripe_customer_id: e.target.value })}
          />
        </label>
        <label className="field">
          <span className="field-label">Stripe subscription ID</span>
          <input
            type="text"
            value={billingForm.stripe_subscription_id}
            onChange={(e) => setBillingForm({ ...billingForm, stripe_subscription_id: e.target.value })}
          />
        </label>
        <button type="submit" className="btn btn-primary schedule-submit" disabled={billingBusy}>
          {billingBusy ? "Saving…" : "Save billing settings"}
        </button>
      </form>
      {billingFeedback ? <p className="hint">{billingFeedback}</p> : null}

      <h3 className="section-lede">Activity trend (last 7 days)</h3>
      <ActivityTrendChart points={activityTrend} />

      <h3 className="section-lede">Onboarding progress</h3>
      <div className="onboarding-list">
        {onboarding.map((item) => (
          <div key={item.key} className={`onboarding-item ${item.completed ? "onboarding-item--done" : ""}`}>
            <strong>{item.completed ? "Done" : "Pending"}</strong> {item.label}
            {item.completed_at ? <span className="hint"> · {formatUtcIsoAsLocal(item.completed_at)}</span> : null}
          </div>
        ))}
      </div>
    </section>
  );
}

BusinessOpsPanel.propTypes = {
  adminOverview: PropTypes.object,
  billingForm: PropTypes.object.isRequired,
  setBillingForm: PropTypes.func.isRequired,
  billingBusy: PropTypes.bool.isRequired,
  billingFeedback: PropTypes.string.isRequired,
  onSaveBilling: PropTypes.func.isRequired,
};

CreateUserSection.propTypes = {
  apiBaseUrl: PropTypes.string.isRequired,
  existingUsers: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      email: PropTypes.string.isRequired,
      role: PropTypes.string.isRequired,
    }),
  ).isRequired,
  userListLoading: PropTypes.bool.isRequired,
  feedback: PropTypes.shape({ kind: PropTypes.string, text: PropTypes.string }).isRequired,
  userForm: PropTypes.shape({
    email: PropTypes.string,
    password: PropTypes.string,
    role: PropTypes.string,
  }).isRequired,
  setUserForm: PropTypes.func.isRequired,
  busy: PropTypes.bool.isRequired,
  onSubmit: PropTypes.func.isRequired,
  currentUserId: PropTypes.number,
  actionBusyId: PropTypes.oneOfType([PropTypes.number, PropTypes.oneOf([null])]),
  onResetPassword: PropTypes.func.isRequired,
  onToggleActive: PropTypes.func.isRequired,
  onDeleteUser: PropTypes.func.isRequired,
  userAuditLogs: PropTypes.arrayOf(PropTypes.object).isRequired,
  userAuditLoading: PropTypes.bool.isRequired,
  billing: PropTypes.object,
  planUsage: PropTypes.object,
};

function DashboardBody({
  summary,
  schedulerHealth,
  adminOverview,
  reportCatalog,
  selectedReportKey,
  setSelectedReportKey,
  selectedReport,
  reportParams,
  setReportParams,
  reportError,
  reportNotice,
  reportBusy,
  onRunReport,
  onExportReportCsv,
  reportResult,
  canManageUsers,
  reportRuns,
  reportRunsLoading,
  reportRunsStatus,
  reportSchedules,
  scheduleForm,
  setScheduleForm,
  scheduleFeedback,
  scheduleBusy,
  scheduleActionBusyId,
  onCreateSchedule,
  onToggleSchedule,
  onRefreshReportRuns,
  canCreateIncident,
  form,
  setForm,
  onCreateIncident,
  incidents,
  incidentFilters,
  onIncidentFilterChange,
  onClearIncidentFilters,
  canEditIncidents,
  editingIncidentId,
  incidentEditForm,
  incidentEditError,
  onStartIncidentEdit,
  onChangeIncidentEditField,
  onSaveIncidentEdit,
  onCancelIncidentEdit,
  canResolve,
  onResolveIncident,
}) {
  const [reportAuditViewLimit, setReportAuditViewLimit] = useState(() => {
    const store = globalThis.window?.localStorage;
    if (!store || typeof store.getItem !== "function") return "3";
    const raw = store.getItem(REPORT_AUDIT_VIEW_LIMIT_KEY) || "3";
    return REPORT_AUDIT_VIEW_LIMIT_OPTIONS.has(raw) ? raw : "3";
  });

  const visibleReportRuns =
    reportAuditViewLimit === "all"
      ? reportRuns
      : reportRuns.slice(0, Number.parseInt(reportAuditViewLimit, 10));
  const scheduleLocalPreview = utcWallClockToLocalPreview(
    Number(scheduleForm.run_hour_utc),
    Number(scheduleForm.run_minute_utc),
  );

  useEffect(() => {
    const store = globalThis.window?.localStorage;
    if (!store || typeof store.setItem !== "function") return;
    store.setItem(REPORT_AUDIT_VIEW_LIMIT_KEY, reportAuditViewLimit);
  }, [reportAuditViewLimit]);

  return (
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

      {canManageUsers ? <SchedulerHealthPanel schedulerHealth={schedulerHealth} /> : null}
      <SqlReportsSection
        reportCatalog={reportCatalog}
        selectedReportKey={selectedReportKey}
        setSelectedReportKey={setSelectedReportKey}
        selectedReport={selectedReport}
        reportParams={reportParams}
        setReportParams={setReportParams}
        reportNotice={reportNotice}
        reportError={reportError}
        reportBusy={reportBusy}
        onRunReport={onRunReport}
        onExportReportCsv={onExportReportCsv}
        reportResult={reportResult}
      />

      {canManageUsers ? (
        <ScheduledReportsSection
          reportCatalog={reportCatalog}
          scheduleForm={scheduleForm}
          setScheduleForm={setScheduleForm}
          scheduleLocalPreview={scheduleLocalPreview}
          onCreateSchedule={onCreateSchedule}
          scheduleBusy={scheduleBusy}
          scheduleFeedback={scheduleFeedback}
          reportSchedules={reportSchedules}
          scheduleActionBusyId={scheduleActionBusyId}
          onToggleSchedule={onToggleSchedule}
          billing={adminOverview?.billing}
          planUsage={adminOverview?.plan_usage}
        />
      ) : null}

      {canManageUsers ? (
        <ReportAuditSection
          reportAuditViewLimit={reportAuditViewLimit}
          setReportAuditViewLimit={setReportAuditViewLimit}
          onRefreshReportRuns={onRefreshReportRuns}
          reportRunsLoading={reportRunsLoading}
          visibleReportRuns={visibleReportRuns}
          reportRuns={reportRuns}
          reportRunsStatus={reportRunsStatus}
        />
      ) : null}

      {canCreateIncident ? (
        <section className="panel">
          <h2 className="panel-title">Create Incident</h2>
          <form className="form-grid" onSubmit={onCreateIncident}>
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

      <IncidentsSection
        incidents={incidents}
        incidentFilters={incidentFilters}
        onIncidentFilterChange={onIncidentFilterChange}
        onClearIncidentFilters={onClearIncidentFilters}
        canEditIncidents={canEditIncidents}
        editingIncidentId={editingIncidentId}
        incidentEditForm={incidentEditForm}
        incidentEditError={incidentEditError}
        onStartIncidentEdit={onStartIncidentEdit}
        onChangeIncidentEditField={onChangeIncidentEditField}
        onSaveIncidentEdit={onSaveIncidentEdit}
        onCancelIncidentEdit={onCancelIncidentEdit}
        canResolve={canResolve}
        onResolveIncident={onResolveIncident}
      />
    </>
  );
}

DashboardBody.propTypes = {
  summary: PropTypes.object,
  schedulerHealth: PropTypes.object,
  adminOverview: PropTypes.object,
  reportCatalog: PropTypes.arrayOf(PropTypes.object).isRequired,
  selectedReportKey: PropTypes.string.isRequired,
  setSelectedReportKey: PropTypes.func.isRequired,
  selectedReport: PropTypes.object,
  reportParams: PropTypes.object.isRequired,
  setReportParams: PropTypes.func.isRequired,
  reportError: PropTypes.string.isRequired,
  reportNotice: PropTypes.string.isRequired,
  reportBusy: PropTypes.bool.isRequired,
  onRunReport: PropTypes.func.isRequired,
  onExportReportCsv: PropTypes.func.isRequired,
  reportResult: PropTypes.object,
  canManageUsers: PropTypes.bool.isRequired,
  reportRuns: PropTypes.arrayOf(PropTypes.object).isRequired,
  reportRunsLoading: PropTypes.bool.isRequired,
  reportRunsStatus: PropTypes.string.isRequired,
  reportSchedules: PropTypes.arrayOf(PropTypes.object).isRequired,
  scheduleForm: PropTypes.object.isRequired,
  setScheduleForm: PropTypes.func.isRequired,
  scheduleFeedback: PropTypes.string.isRequired,
  scheduleBusy: PropTypes.bool.isRequired,
  scheduleActionBusyId: PropTypes.oneOfType([PropTypes.number, PropTypes.oneOf([null])]),
  onCreateSchedule: PropTypes.func.isRequired,
  onToggleSchedule: PropTypes.func.isRequired,
  onRefreshReportRuns: PropTypes.func.isRequired,
  canCreateIncident: PropTypes.bool.isRequired,
  form: PropTypes.object.isRequired,
  setForm: PropTypes.func.isRequired,
  onCreateIncident: PropTypes.func.isRequired,
  incidents: PropTypes.arrayOf(PropTypes.object).isRequired,
  incidentFilters: PropTypes.object.isRequired,
  onIncidentFilterChange: PropTypes.func.isRequired,
  onClearIncidentFilters: PropTypes.func.isRequired,
  canEditIncidents: PropTypes.bool.isRequired,
  editingIncidentId: PropTypes.oneOfType([PropTypes.number, PropTypes.oneOf([null])]),
  incidentEditForm: PropTypes.object.isRequired,
  incidentEditError: PropTypes.string.isRequired,
  onStartIncidentEdit: PropTypes.func.isRequired,
  onChangeIncidentEditField: PropTypes.func.isRequired,
  onSaveIncidentEdit: PropTypes.func.isRequired,
  onCancelIncidentEdit: PropTypes.func.isRequired,
  canResolve: PropTypes.bool.isRequired,
  onResolveIncident: PropTypes.func.isRequired,
};

export default function App() {
  const [token, setToken] = useState(() => {
    const store = globalThis.window?.localStorage;
    if (!store || typeof store.getItem !== "function") return "";
    return store.getItem("dbops_token") || "";
  });
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
  const [reportRunsLoading, setReportRunsLoading] = useState(false);
  const [reportRunsStatus, setReportRunsStatus] = useState("");
  const [reportSchedules, setReportSchedules] = useState([]);
  const [reportError, setReportError] = useState("");
  const [reportNotice, setReportNotice] = useState("");
  const [reportBusy, setReportBusy] = useState(false);
  const [connectionHealth, setConnectionHealth] = useState({ kind: "loading" });
  const [schedulerHealth, setSchedulerHealth] = useState(null);
  const [adminOverview, setAdminOverview] = useState(null);
  const [billingBusy, setBillingBusy] = useState(false);
  const [billingFeedback, setBillingFeedback] = useState("");
  const [billingForm, setBillingForm] = useState({
    plan_key: "starter",
    billing_status: "trialing",
    monthly_price_cents: 14900,
    max_users: 10,
    max_schedules: 10,
    stripe_customer_id: "",
    stripe_subscription_id: "",
  });
  const [userCreateFeedback, setUserCreateFeedback] = useState({ kind: "", text: "" });
  const [userCreateBusy, setUserCreateBusy] = useState(false);
  const [userDirectory, setUserDirectory] = useState([]);
  const [userDirectoryLoading, setUserDirectoryLoading] = useState(false);
  const [userAuditLogs, setUserAuditLogs] = useState([]);
  const [userAuditLoading, setUserAuditLoading] = useState(false);
  const [userActionBusyId, setUserActionBusyId] = useState(null);
  const [scheduleActionBusyId, setScheduleActionBusyId] = useState(null);
  const [scheduleBusy, setScheduleBusy] = useState(false);
  const [scheduleFeedback, setScheduleFeedback] = useState("");
  const [incidentFilters, setIncidentFilters] = useState({
    search: "",
    status: "",
    severity: "",
    owner: "",
    startDate: "",
    endDate: "",
    sort: "newest",
  });
  const [editingIncidentId, setEditingIncidentId] = useState(null);
  const [incidentEditForm, setIncidentEditForm] = useState({
    title: "",
    description: "",
    severity: "medium",
    owner: "unassigned",
  });
  const [incidentEditError, setIncidentEditError] = useState("");
  const [scheduleForm, setScheduleForm] = useState({
    report_key: "",
    cadence: "daily",
    weekday_utc: 0,
    run_hour_utc: 9,
    run_minute_utc: 0,
    delivery_kind: "none",
    delivery_target: "",
    notify_on_success: false,
    notify_on_failure: true,
  });

  function clearClientState() {
    setToken("");
    setMe(null);
    setIncidents([]);
    setSummary(null);
    setReportCatalog([]);
    setSelectedReportKey("");
    setReportParams({});
    setReportResult(null);
    setReportRuns([]);
    setReportRunsLoading(false);
    setReportRunsStatus("");
    setReportSchedules([]);
    setReportError("");
    setReportNotice("");
    setReportBusy(false);
    setUserCreateFeedback({ kind: "", text: "" });
    setUserCreateBusy(false);
    setUserActionBusyId(null);
    setUserDirectory([]);
    setUserDirectoryLoading(false);
    setUserAuditLogs([]);
    setUserAuditLoading(false);
    setEditingIncidentId(null);
    setIncidentEditForm({ title: "", description: "", severity: "medium", owner: "unassigned" });
    setIncidentEditError("");
  }

  function forceLogoutWithMessage(detail = "") {
    clearClientState();
    setAuthError(sessionErrorMessage(detail));
  }

  async function apiJson(path, options = {}) {
    const {
      method = "GET",
      body,
      withAuth = true,
      parseJson = true,
      handleUnauthorized = true,
    } = options;

    const res = await fetch(`${API_URL}${path}`, {
      method,
      headers: headers(withAuth ? token : "", body != null),
      body: body == null ? undefined : JSON.stringify(body),
    });

    const parsed = parseJson ? await parseResponseBody(res) : null;
    if (handleUnauthorized && (res.status === 401 || res.status === 403)) {
      const detail = typeof parsed?.detail === "string" ? parsed.detail : "";
      if (res.status === 401 || detail.toLowerCase().includes("disabled")) {
        forceLogoutWithMessage(detail);
      }
    }
    return { res, body: parsed };
  }

  useEffect(() => {
    const store = globalThis.window?.localStorage;
    if (!store) return;
    if (token && typeof store.setItem === "function") store.setItem("dbops_token", token);
    if (!token && typeof store.removeItem === "function") store.removeItem("dbops_token");
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
    const { res, body } = await apiJson("/auth/me", { parseJson: true });
    if (!res.ok) {
      return;
    }
    setMe(body);
  }

  async function loadData() {
    if (!token) {
      setIncidents([]);
      setSummary(null);
      return;
    }
    const incidentQuery = toIncidentQuery(incidentFilters);
    const [incidentsReq, summaryReq] = await Promise.all([
      apiJson(`/incidents${incidentQuery}`),
      apiJson("/reports/summary"),
    ]);
    if (!incidentsReq.res.ok || !summaryReq.res.ok) {
      return;
    }
    setIncidents(incidentsReq.body);
    setSummary(summaryReq.body);
  }

  async function loadReportCatalog() {
    if (!token) {
      setReportCatalog([]);
      setSelectedReportKey("");
      setReportResult(null);
      setReportError("");
      return;
    }
    const { res, body } = await apiJson("/reports/catalog");
    if (!res.ok) {
      return;
    }
    setReportCatalog(body);
  }

  async function loadReportRuns() {
    if (!token || me?.role !== "DBA") {
      setReportRuns([]);
      setReportRunsLoading(false);
      setReportRunsStatus("");
      return;
    }
    setReportRunsLoading(true);
    setReportRunsStatus("Refreshing audit trail…");
    try {
      const { res, body } = await apiJson("/reports/runs?limit=50");
      if (!res.ok) {
        setReportRunsStatus(`Refresh failed (${res.status}).`);
        return;
      }
      const rows = Array.isArray(body) ? body : [];
      const stamp = new Date().toLocaleTimeString();
      setReportRuns(rows);
      setReportRunsStatus(`Loaded ${rows.length} run(s) at ${stamp}.`);
    } catch {
      setReportRunsStatus("Refresh failed (network). Please try again.");
    } finally {
      setReportRunsLoading(false);
    }
  }

  async function loadReportSchedules() {
    if (!token || me?.role !== "DBA") {
      setReportSchedules([]);
      return;
    }
    const { res, body } = await apiJson("/reports/schedules");
    if (!res.ok) return;
    setReportSchedules(body);
  }

  async function loadSchedulerHealth() {
    if (!token || me?.role !== "DBA") {
      setSchedulerHealth(null);
      return;
    }
    const { res, body } = await apiJson("/health/scheduler");
    if (!res.ok) return;
    setSchedulerHealth(body);
  }

  async function loadAdminOverview() {
    if (!token || me?.role !== "DBA") {
      setAdminOverview(null);
      return;
    }
    const { res, body } = await apiJson("/admin/overview");
    if (!res.ok) return;
    setAdminOverview(body);
    setBillingForm({
      plan_key: body.billing.plan_key,
      billing_status: body.billing.billing_status,
      monthly_price_cents: body.billing.monthly_price_cents,
      max_users: body.billing.max_users,
      max_schedules: body.billing.max_schedules,
      stripe_customer_id: body.billing.stripe_customer_id || "",
      stripe_subscription_id: body.billing.stripe_subscription_id || "",
    });
  }

  async function loadUserDirectory() {
    if (!token || me?.role !== "DBA") {
      setUserDirectory([]);
      setUserDirectoryLoading(false);
      return;
    }
    setUserDirectoryLoading(true);
    const { res, body } = await apiJson("/auth/users");
    if (!res.ok) {
      setUserDirectoryLoading(false);
      return;
    }
    setUserDirectory(body);
    setUserDirectoryLoading(false);
  }

  async function loadUserAuditLogs() {
    if (!token || me?.role !== "DBA") {
      setUserAuditLogs([]);
      setUserAuditLoading(false);
      return;
    }
    setUserAuditLoading(true);
    const { res, body } = await apiJson("/auth/users/audit?limit=100");
    if (!res.ok) {
      setUserAuditLoading(false);
      return;
    }
    setUserAuditLogs(body);
    setUserAuditLoading(false);
  }

  useEffect(() => {
    loadMe();
  }, [token]);

  useEffect(() => {
    loadData();
  }, [token, me, incidentFilters]);

  useEffect(() => {
    loadReportCatalog();
  }, [token]);

  useEffect(() => {
    loadReportRuns();
  }, [token, me]);

  useEffect(() => {
    loadReportSchedules();
  }, [token, me]);

  useEffect(() => {
    loadUserDirectory();
  }, [token, me]);

  useEffect(() => {
    loadUserAuditLogs();
  }, [token, me]);

  useEffect(() => {
    loadSchedulerHealth();
  }, [token, me]);

  useEffect(() => {
    loadAdminOverview();
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
    setScheduleForm((prev) => ({ ...prev, report_key: spec.key }));
  }, [selectedReportKey, reportCatalog]);

  useEffect(() => {
    if (!reportCatalog.length) return;
    setScheduleForm((prev) => {
      if (prev.report_key && reportCatalog.some((r) => r.key === prev.report_key)) {
        return prev;
      }
      return { ...prev, report_key: reportCatalog[0].key };
    });
  }, [reportCatalog]);

  async function login(e) {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: headers("", true),
        body: JSON.stringify(loginForm),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setAuthError(authErrorMessage(res.status, body, "Login failed."));
        return;
      }

      const data = await res.json();
      setToken(data.access_token);
      setLoginForm({ email: "", password: "" });
    } catch {
      setAuthError(`Could not reach the API (${API_URL}). Check your connection and deployed API URL.`);
    }
  }

  async function bootstrapRegister(e) {
    e.preventDefault();
    setAuthError("");
    if (bootstrapForm.password !== bootstrapForm.confirm) {
      setAuthError("Passwords do not match");
      return;
    }
    try {
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
        setAuthError(authErrorMessage(res.status, body, "Registration failed."));
        return;
      }

      setBootstrapForm({ email: "", password: "", confirm: "" });
      setAuthError("");
      alert("Admin created. Sign in below.");
    } catch {
      setAuthError(`Could not reach the API (${API_URL}). Check your connection and deployed API URL.`);
    }
  }

  async function createUser(e) {
    e.preventDefault();
    setUserCreateFeedback({ kind: "", text: "" });
    setUserCreateBusy(true);
    const ctrl = new AbortController();
    const timeoutId = setTimeout(() => ctrl.abort(), CREATE_USER_FETCH_MS);
    try {
      const res = await fetch(`${API_URL}/auth/users`, {
        method: "POST",
        headers: headers(token, true),
        body: JSON.stringify({
          email: userForm.email.trim(),
          password: userForm.password,
          role: userForm.role,
        }),
        signal: ctrl.signal,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        if (res.status === 401 || (res.status === 403 && String(body?.detail || "").toLowerCase().includes("disabled"))) {
          forceLogoutWithMessage(String(body?.detail || ""));
          return;
        }
        let msg = formatApiDetail(body);
        if (!msg || msg === "Request failed") msg = `Server returned ${res.status}.`;
        setUserCreateFeedback({ kind: "error", text: msg });
        return;
      }
      const created = await res.json().catch(() => ({}));
      const emailLabel = created.email || userForm.email;
      const roleLabel = created.role || userForm.role;
      setUserCreateFeedback({
        kind: "success",
        text: `Created ${emailLabel} (${roleLabel}). They can sign in now.`,
      });
      setUserForm({ email: "", password: "", role: "Viewer" });
      await loadUserDirectory();
      await loadUserAuditLogs();
      await loadAdminOverview();
    } catch (err) {
      let reason = err instanceof Error ? err.message : String(err);
      if (String(err?.name) === "AbortError") {
        reason = `No response after ${CREATE_USER_FETCH_MS / 1000}s (timed out).`;
      }
      setUserCreateFeedback({
        kind: "error",
        text:
          `Could not reach the API (${API_URL}). ${reason} ` +
          "Open DevTools → Network for POST /auth/users. On Render, set VITE_API_URL on dbops-web and redeploy.",
      });
    } finally {
      clearTimeout(timeoutId);
      setUserCreateBusy(false);
    }
  }

  async function resetUserPassword(user) {
    const next = globalThis.window?.prompt(`Enter new password for ${user.email} (min 8 characters):`);
    if (!next) return;
    setUserActionBusyId(user.id);
    setUserCreateFeedback({ kind: "", text: "" });
    const res = await fetch(`${API_URL}/auth/users/${user.id}/password`, {
      method: "PATCH",
      headers: headers(token, true),
      body: JSON.stringify({ password: next }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setUserCreateFeedback({ kind: "error", text: formatApiDetail(body) });
      setUserActionBusyId(null);
      return;
    }
    setUserCreateFeedback({ kind: "success", text: `Password updated for ${user.email}.` });
    await loadUserAuditLogs();
    setUserActionBusyId(null);
  }

  async function toggleUserActive(user) {
    setUserActionBusyId(user.id);
    setUserCreateFeedback({ kind: "", text: "" });
    const res = await fetch(`${API_URL}/auth/users/${user.id}/status`, {
      method: "PATCH",
      headers: headers(token, true),
      body: JSON.stringify({ is_active: !user.is_active }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setUserCreateFeedback({ kind: "error", text: formatApiDetail(body) });
      setUserActionBusyId(null);
      return;
    }
    await loadUserDirectory();
    await loadUserAuditLogs();
    await loadAdminOverview();
    setUserCreateFeedback({
      kind: "success",
      text: `${user.email} is now ${user.is_active ? "disabled" : "active"}.`,
    });
    setUserActionBusyId(null);
  }

  async function deleteUser(user) {
    const ok = globalThis.window?.confirm(`Delete ${user.email}? This cannot be undone.`);
    if (!ok) return;
    setUserActionBusyId(user.id);
    setUserCreateFeedback({ kind: "", text: "" });
    const res = await fetch(`${API_URL}/auth/users/${user.id}`, {
      method: "DELETE",
      headers: headers(token, false),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setUserCreateFeedback({ kind: "error", text: formatApiDetail(body) });
      setUserActionBusyId(null);
      return;
    }
    await loadUserDirectory();
    await loadUserAuditLogs();
    await loadAdminOverview();
    setUserCreateFeedback({ kind: "success", text: `${user.email} deleted.` });
    setUserActionBusyId(null);
  }

  function logout() {
    clearClientState();
    setAuthError("");
  }

  async function runReport(e) {
    e.preventDefault();
    setReportError("");
    setReportNotice("");
    setReportBusy(true);
    const spec = reportCatalog.find((r) => r.key === selectedReportKey);
    const paramsPayload = reportParamsPayload(spec, reportParams);
    try {
      const { res, body } = await apiJson("/reports/run", {
        method: "POST",
        body: { report_key: selectedReportKey, params: paramsPayload },
      });
      if (!res.ok) {
        setReportResult(null);
        setReportError(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail) || "Report failed");
        return;
      }
      setReportResult(body);
      setReportNotice(`Loaded ${body.row_count} row(s) in ${body.duration_ms} ms.`);
      if (me?.role === "DBA") {
        loadReportRuns();
        loadAdminOverview();
      }
    } finally {
      setReportBusy(false);
    }
  }

  async function exportReportCsv() {
    setReportError("");
    setReportNotice("");
    setReportBusy(true);
    const spec = reportCatalog.find((r) => r.key === selectedReportKey);
    const paramsPayload = reportParamsPayload(spec, reportParams);
    try {
      const { res } = await apiJson("/reports/export/csv", {
        method: "POST",
        body: { report_key: selectedReportKey, params: paramsPayload },
        parseJson: false,
      });
      if (!res.ok) {
        const body = await parseResponseBody(res);
        setReportError(typeof body.detail === "string" ? body.detail : "CSV export failed");
        return;
      }
      const csvText = await res.text();
      const filename = csvFilenameFromContentDisposition(
        res.headers?.get?.("content-disposition") || "",
        selectedReportKey,
      );
      const blob = new Blob([csvText], { type: "text/csv;charset=utf-8" });
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
      setReportNotice(`Downloaded ${filename}.`);
      if (me?.role === "DBA") {
        loadReportRuns();
      }
    } finally {
      setReportBusy(false);
    }
  }

  async function createIncident(e) {
    e.preventDefault();
    const { res, body } = await apiJson("/incidents", { method: "POST", body: form });
    if (!res.ok) {
      setIncidentEditError(formatApiDetail(body));
      return;
    }
    setForm({
      title: "",
      description: "",
      severity: "medium",
      owner: "unassigned",
    });
    await loadData();
    if (me?.role === "DBA") await loadAdminOverview();
  }

  async function createReportSchedule(e) {
    e.preventDefault();
    setScheduleFeedback("");
    setScheduleBusy(true);
    const selected = reportCatalog.find((r) => r.key === scheduleForm.report_key);
    const payload = {
      report_key: scheduleForm.report_key,
      params: reportParamsPayload(selected, reportParams),
      cadence: scheduleForm.cadence,
      weekday_utc: scheduleForm.cadence === "weekly" ? scheduleForm.weekday_utc : null,
      run_hour_utc: scheduleForm.run_hour_utc,
      run_minute_utc: scheduleForm.run_minute_utc,
      delivery_kind: scheduleForm.delivery_kind,
      delivery_target: scheduleForm.delivery_kind === "none" ? null : scheduleForm.delivery_target,
      notify_on_success: scheduleForm.notify_on_success,
      notify_on_failure: scheduleForm.notify_on_failure,
    };
    const { res, body } = await apiJson("/reports/schedules", { method: "POST", body: payload });
    if (!res.ok) {
      setScheduleFeedback(`Schedule create failed: ${formatApiDetail(body)}`);
      setScheduleBusy(false);
      return;
    }
    setScheduleFeedback("Schedule created.");
    setScheduleBusy(false);
    await loadReportSchedules();
    await loadAdminOverview();
  }

  async function toggleReportSchedule(schedule) {
    setScheduleActionBusyId(schedule.id);
    setScheduleFeedback("");
    const { res, body } = await apiJson(`/reports/schedules/${schedule.id}/status`, {
      method: "PATCH",
      body: { is_enabled: !schedule.is_enabled },
    });
    if (!res.ok) {
      setScheduleFeedback(`Schedule update failed: ${formatApiDetail(body)}`);
      setScheduleActionBusyId(null);
      return;
    }
    setScheduleFeedback(`Schedule ${body.is_enabled ? "enabled" : "disabled"}.`);
    setScheduleActionBusyId(null);
    await loadReportSchedules();
    await loadAdminOverview();
  }

  async function saveBillingSettings(e) {
    e.preventDefault();
    setBillingFeedback("");
    setBillingBusy(true);
    const { res, body } = await apiJson("/admin/billing", { method: "PUT", body: billingForm });
    if (!res.ok) {
      setBillingFeedback(`Billing update failed: ${formatApiDetail(body)}`);
      setBillingBusy(false);
      return;
    }
    setBillingFeedback("Billing settings saved.");
    setBillingBusy(false);
    await loadAdminOverview();
  }

  async function resolveIncident(id) {
    const { res } = await apiJson(`/incidents/${id}/resolve`, { method: "PATCH", parseJson: false });
    if (!res.ok) return;
    await loadData();
    if (me?.role === "DBA") await loadAdminOverview();
  }

  function startIncidentEdit(incident) {
    setIncidentEditError("");
    setEditingIncidentId(incident.id);
    setIncidentEditForm({
      title: incident.title,
      description: incident.description,
      severity: incident.severity,
      owner: incident.owner,
    });
  }

  function changeIncidentEditField(field, value) {
    setIncidentEditForm((prev) => ({ ...prev, [field]: value }));
  }

  function cancelIncidentEdit() {
    setEditingIncidentId(null);
    setIncidentEditError("");
  }

  async function saveIncidentEdit(incidentId) {
    setIncidentEditError("");
    const { res, body } = await apiJson(`/incidents/${incidentId}`, {
      method: "PATCH",
      body: {
        title: incidentEditForm.title,
        description: incidentEditForm.description,
        severity: incidentEditForm.severity,
        owner: incidentEditForm.owner,
      },
    });
    if (!res.ok) {
      setIncidentEditError(formatApiDetail(body));
      return;
    }
    setEditingIncidentId(null);
    await loadData();
    if (me?.role === "DBA") await loadAdminOverview();
  }

  function setIncidentFilterField(field, value) {
    setIncidentFilters((prev) => ({ ...prev, [field]: value }));
  }

  function clearIncidentFilters() {
    setIncidentFilters({
      search: "",
      status: "",
      severity: "",
      owner: "",
      startDate: "",
      endDate: "",
      sort: "newest",
    });
  }

  const role = me?.role;
  const canCreateIncident = role === "DBA" || role === "Analyst";
  const canEditIncidents = role === "DBA" || role === "Analyst";
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

      {token ? (
        <>
          <div className="top-bar panel">
            <span className="top-bar-meta">
              Signed in as <strong>{me?.email}</strong> ({me?.role})
            </span>
            <button type="button" className="btn btn-ghost" onClick={logout}>
              Log out
            </button>
          </div>
          {canManageUsers ? (
            <BusinessOpsPanel
              adminOverview={adminOverview}
              billingForm={billingForm}
              setBillingForm={setBillingForm}
              billingBusy={billingBusy}
              billingFeedback={billingFeedback}
              onSaveBilling={saveBillingSettings}
            />
          ) : null}
          {canManageUsers ? (
            <CreateUserSection
              apiBaseUrl={API_URL}
              existingUsers={userDirectory}
              userListLoading={userDirectoryLoading}
              feedback={userCreateFeedback}
              userForm={userForm}
              setUserForm={setUserForm}
              busy={userCreateBusy}
              onSubmit={createUser}
              currentUserId={me?.id}
              actionBusyId={userActionBusyId}
              onResetPassword={resetUserPassword}
              onToggleActive={toggleUserActive}
              onDeleteUser={deleteUser}
              userAuditLogs={userAuditLogs}
              userAuditLoading={userAuditLoading}
              billing={adminOverview?.billing}
              planUsage={adminOverview?.plan_usage}
            />
          ) : null}
          <DashboardBody
            summary={summary}
            schedulerHealth={schedulerHealth}
            adminOverview={adminOverview}
            reportCatalog={reportCatalog}
            selectedReportKey={selectedReportKey}
            setSelectedReportKey={setSelectedReportKey}
            selectedReport={selectedReport}
            reportParams={reportParams}
            setReportParams={setReportParams}
            reportError={reportError}
            reportNotice={reportNotice}
            reportBusy={reportBusy}
            onRunReport={runReport}
            onExportReportCsv={exportReportCsv}
            reportResult={reportResult}
            canManageUsers={canManageUsers}
            reportRuns={reportRuns}
            reportRunsLoading={reportRunsLoading}
            reportRunsStatus={reportRunsStatus}
            reportSchedules={reportSchedules}
            scheduleForm={scheduleForm}
            setScheduleForm={setScheduleForm}
            scheduleFeedback={scheduleFeedback}
            scheduleBusy={scheduleBusy}
            scheduleActionBusyId={scheduleActionBusyId}
            onCreateSchedule={createReportSchedule}
            onToggleSchedule={toggleReportSchedule}
            onRefreshReportRuns={loadReportRuns}
            canCreateIncident={canCreateIncident}
            form={form}
            setForm={setForm}
            onCreateIncident={createIncident}
            incidents={incidents}
            incidentFilters={incidentFilters}
            onIncidentFilterChange={setIncidentFilterField}
            onClearIncidentFilters={clearIncidentFilters}
            canEditIncidents={canEditIncidents}
            editingIncidentId={editingIncidentId}
            incidentEditForm={incidentEditForm}
            incidentEditError={incidentEditError}
            onStartIncidentEdit={startIncidentEdit}
            onChangeIncidentEditField={changeIncidentEditField}
            onSaveIncidentEdit={saveIncidentEdit}
            onCancelIncidentEdit={cancelIncidentEdit}
            canResolve={canResolve}
            onResolveIncident={resolveIncident}
          />
        </>
      ) : (
        <LoginPanel
          connectionHealth={connectionHealth}
          apiUrl={API_URL}
          authError={authError}
          loginForm={loginForm}
          setLoginForm={setLoginForm}
          onLogin={login}
          bootstrapForm={bootstrapForm}
          setBootstrapForm={setBootstrapForm}
          onBootstrap={bootstrapRegister}
        />
      )}
    </main>
  );
}
