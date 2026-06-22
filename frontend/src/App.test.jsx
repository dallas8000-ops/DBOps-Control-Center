import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderApp } from "./test/renderApp";

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  };
}

function routeKey(method, path) {
  return `${method} ${path}`;
}

function clearStoredState() {
  const store = globalThis.window?.localStorage;
  if (!store || typeof store.removeItem !== "function") return;
  store.removeItem("dbops_token");
  store.removeItem("dbops_report_audit_view_limit");
}

function installLocalStorageMock() {
  const values = new Map();
  Object.defineProperty(globalThis.window, "localStorage", {
    configurable: true,
    value: {
      getItem(key) {
        return values.has(key) ? values.get(key) : null;
      },
      setItem(key, value) {
        values.set(key, String(value));
      },
      removeItem(key) {
        values.delete(key);
      },
    },
  });
}

async function login(email, password = "Password123!") {
  fireEvent.change(screen.getByPlaceholderText("Email"), { target: { value: email } });
  fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Login" }));
  await waitFor(() => {
    expect(screen.getByText(/Signed in as/i)).toBeInTheDocument();
  });
}

function expandAccordion(sectionTitle) {
  const toggle = screen.getByRole("button", { name: sectionTitle });
  if (toggle.getAttribute("aria-expanded") === "false") {
    fireEvent.click(toggle);
  }
}

async function expandAccordionAndWaitForHeading(sectionTitle, headingName) {
  expandAccordion(sectionTitle);
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: headingName })).toBeInTheDocument();
  });
}

function createFetchMock({
  meRole = "Analyst",
  meEmail = "analyst@example.com",
  reportRows = [{ status: "open", total: 1 }],
  auditRuns = [],
  bulkActionStatus = 200,
  loginResponse = jsonResponse({ access_token: "token-123", token_type: "bearer" }),
  aiFindReportStatus = 200,
  aiFindReportResponse = {
    report_key: "incidents_by_status",
    title: "Incidents by status",
    description: "Aggregated incident status counts",
    matched_by: "heuristic",
    confidence: 0.66,
  },
  aiIncidentSummaryStatus = 200,
  aiIncidentSummaryResponse = {
    incident_id: 1,
    source: "heuristic",
    summary_lines: [
      "Incident 1 remains open and high severity.",
      "Most recent actions include create and acknowledge.",
      "Next handoff should confirm ownership and mitigation ETA.",
    ],
  },
} = {}) {
  let incidentRow = {
    id: 1,
    title: "Replication lag",
    description: "Lag exceeded threshold",
    severity: "high",
    owner: "ops",
    status: "open",
    created_at: "2026-05-08T10:00:00",
  };
  let incidentHistoryEntries = [
    {
      id: 1,
      incident_id: 1,
      actor_email: meEmail,
      action: "created",
      details: {
        title: "Replication lag",
        description: "Lag exceeded threshold",
        severity: "high",
        owner: "ops",
        status: "open",
        due_at: null,
      },
      created_at: "2026-05-08T10:00:00",
    },
  ];

  const schedules = [
    {
      id: 1,
      report_key: "incidents_by_status",
      params: {},
      cadence: "daily",
      weekday_utc: null,
      run_hour_utc: 9,
      run_minute_utc: 0,
      delivery_kind: "none",
      delivery_target: null,
      notify_on_success: false,
      notify_on_failure: true,
      is_enabled: true,
      next_run_at: "2026-05-10T09:00:00",
      last_run_at: null,
      last_success_at: null,
      last_error: null,
      created_at: "2026-05-09T10:00:00",
      created_by_user_id: 2,
      created_by_email: meEmail,
    },
  ];

  const staticResponses = {
    "GET /health": jsonResponse({ status: "ok", database: "reachable" }),
    "GET /health/scheduler": jsonResponse({
      status: "ok",
      scheduler: {
        loop_enabled: true,
        poll_seconds: 60,
        last_iteration_started_at: "2026-05-10T12:00:00",
        last_iteration_completed_at: "2026-05-10T12:00:01",
        last_iteration_processed: 2,
        last_iteration_error: null,
        consecutive_failures: 0,
      },
    }),
    "GET /health/smtp": jsonResponse({
      status: "ok",
      smtp: { smtp_host: null, smtp_port: null, smtp_user: null, smtp_from: null },
    }),
    "GET /admin/overview": jsonResponse({
      metrics: {
        total_users: 3,
        active_users: 3,
        open_incidents: 1,
        resolved_incidents: 0,
        enabled_schedules: 1,
        report_runs_last_24h: 4,
        successful_report_runs_last_24h: 4,
        onboarding_completed_steps: 2,
        onboarding_total_steps: 4,
      },
      billing: {
        id: 1,
        plan_key: "starter",
        billing_status: "trialing",
        monthly_price_cents: 14900,
        max_users: 10,
        max_schedules: 10,
        stripe_customer_id: null,
        stripe_subscription_id: null,
        created_at: "2026-05-10T12:00:00",
        updated_at: "2026-05-10T12:00:00",
      },
      plan_usage: {
        user_slots_used: 3,
        user_slots_remaining: 7,
        users_at_limit: false,
        schedule_slots_used: 1,
        schedule_slots_remaining: 9,
        schedules_at_limit: false,
      },
      onboarding: [
        { key: "first_user_created", label: "Create first team member", completed: true, completed_at: "2026-05-10T12:00:00" },
        { key: "first_incident_created", label: "Create first incident", completed: true, completed_at: "2026-05-10T12:05:00" },
        { key: "first_report_run", label: "Run first report", completed: false, completed_at: null },
        { key: "first_schedule_created", label: "Create first schedule", completed: false, completed_at: null },
      ],
      activity_trend: [
        { day: "2026-05-04", label: "Mon", incidents_created: 0, report_runs: 0, schedules_created: 0 },
        { day: "2026-05-05", label: "Tue", incidents_created: 1, report_runs: 0, schedules_created: 0 },
        { day: "2026-05-06", label: "Wed", incidents_created: 0, report_runs: 2, schedules_created: 0 },
        { day: "2026-05-07", label: "Thu", incidents_created: 1, report_runs: 1, schedules_created: 0 },
        { day: "2026-05-08", label: "Fri", incidents_created: 0, report_runs: 0, schedules_created: 1 },
        { day: "2026-05-09", label: "Sat", incidents_created: 0, report_runs: 1, schedules_created: 0 },
        { day: "2026-05-10", label: "Sun", incidents_created: 0, report_runs: 0, schedules_created: 0 },
      ],
      deployment_readiness: {
        score: 88,
        label: "Production ready",
        tier_readiness: "starter",
        automation_center_url: "https://stripe-installer.gilliomfrontlinedigital.com",
        config_root: null,
        checks: [
          {
            id: "tier-readiness",
            category: "stripe",
            name: "Stripe tier env",
            status: "warn",
            message: "tier_readiness=starter",
            fix: "Set STRIPE_PRICE_ID_PRO",
          },
        ],
      },
    }),
    "GET /auth/me": jsonResponse({ id: 2, email: meEmail, role: meRole, is_active: true }),
    "GET /reports/summary": jsonResponse({
      total_incidents: 1,
      open_incidents: 1,
      resolved_incidents: 0,
      high_severity_incidents: 1,
    }),
    "GET /reports/catalog": jsonResponse([
      {
        key: "incidents_by_status",
        title: "Incidents by status",
        description: "Aggregated incident status counts",
        params: [],
      },
    ]),
    "GET /reports/runs": jsonResponse(auditRuns),
    "GET /reports/schedules": jsonResponse(schedules),
    "GET /auth/users": jsonResponse([]),
    "GET /auth/oidc/config": jsonResponse({ enabled: false }),
  };

  const dynamicHandlers = [
    {
      match: (path, method) => path === "/auth/login" && method === "POST",
      respond: () => loginResponse,
    },
    {
      match: (path, method) => path === "/incidents" && method === "GET",
      respond: () => jsonResponse([incidentRow]),
    },
    {
      match: (path, method) => path === "/incidents" && method === "POST",
      respond: () =>
        jsonResponse(
          {
            id: 2,
            title: "Created from smoke test",
            description: "desc",
            severity: "medium",
            owner: "analyst@example.com",
            status: "open",
            created_at: "2026-05-08T10:05:00",
          },
          201,
        ),
    },
    {
      match: (path, method) => path === "/incidents/1/history" && method === "GET",
      respond: () => jsonResponse(incidentHistoryEntries),
    },
    {
      match: (path, method) => path === "/incidents/1/comments" && method === "POST",
      respond: (reqOptions = {}) => {
        let parsed = {};
        try {
          parsed = JSON.parse(String(reqOptions.body || "{}"));
        } catch {
          parsed = {};
        }
        const comment = String(parsed.comment || "").trim();
        const entry = {
          id: incidentHistoryEntries.length + 1,
          incident_id: 1,
          actor_email: meEmail,
          action: "commented",
          details: { comment },
          created_at: "2026-05-08T10:05:00",
        };
        incidentHistoryEntries = [...incidentHistoryEntries, entry];
        return jsonResponse(entry, 200);
      },
    },
    {
      match: (path, method) => path === "/reports/run" && method === "POST",
      respond: () =>
        jsonResponse({
          report_key: "incidents_by_status",
          columns: ["status", "total"],
          rows: reportRows,
          row_count: reportRows.length,
          truncated: false,
          duration_ms: 7,
        }),
    },
    {
      match: (path, method) => path === "/api/ai/find-report" && method === "POST",
      respond: () => jsonResponse(aiFindReportResponse, aiFindReportStatus),
    },
    {
      match: (path, method) => path.startsWith("/api/ai/summarize-incident/") && method === "POST",
      respond: () => jsonResponse(aiIncidentSummaryResponse, aiIncidentSummaryStatus),
    },
    {
      match: (path, method) => path === "/reports/export/csv" && method === "POST",
      respond: () => ({
        ok: true,
        status: 200,
        text: async () => "status,incident_count\nopen,1\n",
      }),
    },
    {
      match: (path, method) => path === "/reports/schedules" && method === "POST",
      respond: () =>
        jsonResponse(
          {
            ...schedules[0],
            id: 2,
            delivery_kind: "email",
            delivery_target: "ops@example.com",
          },
          201,
        ),
    },
    {
      match: (path, method) => path === "/admin/billing" && method === "PUT",
      respond: () =>
        jsonResponse(
          {
            id: 1,
            plan_key: "starter",
            billing_status: "trialing",
            monthly_price_cents: 14900,
            max_users: 10,
            max_schedules: 10,
            stripe_customer_id: null,
            stripe_subscription_id: null,
            created_at: "2026-05-10T12:00:00",
            updated_at: "2026-05-10T12:01:00",
          },
          200,
        ),
    },
    {
      match: (path, method) => path === "/billing/checkout/session" && method === "POST",
      respond: () =>
        jsonResponse({
          session_id: "cs_test_123",
          url: "https://checkout.stripe.test/session_123",
        }),
    },
    {
      match: (path, method) => path.startsWith("/reports/schedules/") && path.endsWith("/status") && method === "PATCH",
      respond: () => jsonResponse({ ...schedules[0], is_enabled: false }),
    },
    {
      match: (path, method) => path.endsWith("/resolve") && method === "PATCH",
      respond: () => {
        incidentRow = { ...incidentRow, status: "resolved" };
        return jsonResponse(incidentRow);
      },
    },
    {
      match: (path, method) => path === "/incidents/actions/bulk" && method === "PATCH",
      respond: (reqOptions = {}) => {
        let parsed = {};
        try {
          parsed = JSON.parse(String(reqOptions.body || "{}"));
        } catch {
          parsed = {};
        }

        const action = String(parsed.action || "");
        if (action === "resolve") {
          incidentRow = { ...incidentRow, status: "resolved" };
        }
        if (action === "assign" && parsed.owner) {
          incidentRow = { ...incidentRow, owner: String(parsed.owner) };
        }
        if (action === "escalate") {
          incidentRow = { ...incidentRow, severity: "high" };
        }

        if (bulkActionStatus >= 400) {
          return jsonResponse({ detail: "Bulk action failed" }, bulkActionStatus);
        }

        return jsonResponse({
          action,
          affected_count: 1,
          incidents: [incidentRow],
          summary: {
            requested_count: 1,
            unique_count: 1,
            duplicate_count: 0,
            updated_count: 1,
            skipped_count: 0,
          },
          items: [
            {
              incident_id: incidentRow.id,
              outcome: "updated",
              reason: null,
              before: { status: "open", severity: "high", owner: "ops" },
              after: {
                status: incidentRow.status,
                severity: incidentRow.severity,
                owner: incidentRow.owner,
              },
            },
          ],
        });
      },
    },
  ];

  return vi.fn(async (url, options = {}) => {
    const method = (options.method || "GET").toUpperCase();
    const path = new URL(String(url)).pathname;
    const key = routeKey(method, path);
    if (staticResponses[key]) return staticResponses[key];

    const handler = dynamicHandlers.find((candidate) => candidate.match(path, method));
    if (handler) return handler.respond(options);

    return jsonResponse({ detail: `Unhandled route ${method} ${path}` }, 500);
  });
}

beforeEach(() => {
  vi.stubGlobal("alert", vi.fn());
  installLocalStorageMock();
  clearStoredState();
});

afterEach(() => {
  cleanup();
  clearStoredState();
  vi.unstubAllGlobals();
});

describe("App smoke", () => {
  it("renders login panel", async () => {
    vi.stubGlobal("fetch", createFetchMock());
    renderApp();
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "DBOps Control Center" })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Login" })).toBeInTheDocument();
  });

  it("logs in and shows signed-in header", async () => {
    vi.stubGlobal("fetch", createFetchMock());

    renderApp();

    fireEvent.change(screen.getByPlaceholderText("Email"), {
      target: { value: "analyst@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByText(/Signed in as/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/analyst@example.com/)).toBeInTheDocument();
    expect(screen.getByText(/Analyst/)).toBeInTheDocument();
  });

  it("restores a persisted token from localStorage", async () => {
    globalThis.window.localStorage.setItem("dbops_token", "stored-token");
    vi.stubGlobal("fetch", createFetchMock());

    renderApp();

    await waitFor(() => {
      expect(screen.getByText(/Signed in as/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/analyst@example.com/)).toBeInTheDocument();
    expect(globalThis.window.localStorage.getItem("dbops_token")).toBe("stored-token");
  });

  it("shows a disabled-account message on login failure", async () => {
    vi.stubGlobal(
      "fetch",
      createFetchMock({
        loginResponse: jsonResponse({ detail: "Your account is disabled. Contact a DBA." }, 403),
      }),
    );

    renderApp();

    fireEvent.change(screen.getByPlaceholderText("Email"), {
      target: { value: "analyst@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByText("Your account is disabled. Contact a DBA.")).toBeInTheDocument();
    });
  });

  it("shows a friendly rate-limit message on login", async () => {
    vi.stubGlobal(
      "fetch",
      createFetchMock({
        loginResponse: jsonResponse({ detail: "Too many auth requests. Please try again shortly." }, 429),
      }),
    );

    renderApp();

    fireEvent.change(screen.getByPlaceholderText("Email"), {
      target: { value: "analyst@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByText("Too many auth requests. Please try again shortly.")).toBeInTheDocument();
    });
  });

  it("shows a friendly bootstrap-complete message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, options = {}) => {
        const method = (options.method || "GET").toUpperCase();
        const path = new URL(String(url)).pathname;

        if (path === "/health" && method === "GET") {
          return jsonResponse({ status: "ok", database: "reachable" });
        }

        if (path === "/auth/register" && method === "POST") {
          return jsonResponse({ detail: "Bootstrap complete. Use POST /auth/users with a DBA token." }, 403);
        }

        return jsonResponse({ detail: `Unhandled route ${method} ${path}` }, 500);
      }),
    );

    renderApp();

    fireEvent.change(screen.getByPlaceholderText("Admin email"), {
      target: { value: "dba@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Password (min 8 characters)"), {
      target: { value: "Password123!" },
    });
    fireEvent.change(screen.getByPlaceholderText("Confirm password"), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create first DBA" }));

    await waitFor(() => {
      expect(screen.getByText("Setup is already complete. Sign in with an existing DBA account.")).toBeInTheDocument();
    });
  });

  it("clears the stored token and returns to login on expired session", async () => {
    globalThis.window.localStorage.setItem("dbops_token", "expired-token");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, options = {}) => {
        const method = (options.method || "GET").toUpperCase();
        const path = new URL(String(url)).pathname;

        if (path === "/health" && method === "GET") {
          return jsonResponse({ status: "ok", database: "reachable" });
        }

        if (["/auth/me", "/incidents", "/reports/summary", "/reports/catalog"].includes(path) && method === "GET") {
          return jsonResponse({ detail: "Token expired" }, 401);
        }

        return jsonResponse({ detail: `Unhandled route ${method} ${path}` }, 500);
      }),
    );

    renderApp();

    await waitFor(() => {
      expect(screen.getByText("Your session expired. Please sign in again.")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Login" })).toBeInTheDocument();
    expect(globalThis.window.localStorage.getItem("dbops_token")).toBeNull();
  });

  it("submits create incident request", async () => {
    const fetchMock = createFetchMock();
    vi.stubGlobal("fetch", fetchMock);

    renderApp();
    await login("analyst@example.com");
    expandAccordion("Create Incident");
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Title")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText("Title"), {
      target: { value: "Storage threshold warning" },
    });
    fireEvent.change(screen.getByPlaceholderText("Description"), {
      target: { value: "Disk usage crossed 90 percent" },
    });
    fireEvent.change(screen.getByPlaceholderText("Owner"), {
      target: { value: "analyst@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url, options]) =>
            String(url).includes("/incidents") &&
            (options?.method || "GET").toUpperCase() === "POST",
        ),
      ).toBe(true);
    });
  });

  it("posts a comment from the incident history drawer", async () => {
    const fetchMock = createFetchMock({ meRole: "Viewer", meEmail: "viewer@example.com" });
    vi.stubGlobal("fetch", fetchMock);

    renderApp();
    await login("viewer@example.com");
    await expandAccordionAndWaitForHeading("Incidents", "Incidents");

    fireEvent.click(screen.getByRole("button", { name: "History" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Add a comment" })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText("Write a handoff note, follow-up, or context update..."), {
      target: { value: "Investigating with the app team now." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Post comment" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url, options]) =>
            String(url).includes("/incidents/1/comments") &&
            (options?.method || "GET").toUpperCase() === "POST" &&
            String(options?.body || "").includes("Investigating with the app team now."),
        ),
      ).toBe(true);
      expect(screen.getByText("Investigating with the app team now.")).toBeInTheDocument();
    });
  });

  it("shows bulk selection controls for Analyst on eligible incidents", async () => {
    vi.stubGlobal("fetch", createFetchMock({ meRole: "Analyst", meEmail: "analyst@example.com" }));

    renderApp();
    await login("analyst@example.com");
    await expandAccordionAndWaitForHeading("Incidents", "Incidents");

    expect(screen.getByLabelText("Select all eligible incidents")).toBeInTheDocument();
    expect(screen.getByLabelText("Select incident 1")).toBeInTheDocument();
  });

  it("hides bulk selection controls for Viewer", async () => {
    vi.stubGlobal("fetch", createFetchMock({ meRole: "Viewer", meEmail: "viewer@example.com" }));

    renderApp();
    await login("viewer@example.com");
    await expandAccordionAndWaitForHeading("Incidents", "Incidents");

    expect(screen.queryByLabelText("Select all eligible incidents")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Select incident 1")).not.toBeInTheDocument();
  });

  it("sends bulk acknowledge request from quick actions bar", async () => {
    const fetchMock = createFetchMock({ meRole: "Analyst", meEmail: "analyst@example.com" });
    vi.stubGlobal("fetch", fetchMock);

    renderApp();
    await login("analyst@example.com");
    await expandAccordionAndWaitForHeading("Incidents", "Incidents");

    fireEvent.click(screen.getByLabelText("Select incident 1"));
    fireEvent.click(screen.getByRole("button", { name: "Acknowledge selected" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url, options]) =>
            String(url).includes("/incidents/actions/bulk") &&
            (options?.method || "GET").toUpperCase() === "PATCH" &&
            String(options?.body || "").includes("\"action\":\"acknowledge\""),
        ),
      ).toBe(true);
    });

    expect(screen.getByText("Bulk acknowledge: 1 updated.")).toBeInTheDocument();
  });

  it("rolls back optimistic bulk resolve and shows error toast", async () => {
    const fetchMock = createFetchMock({
      meRole: "DBA",
      meEmail: "dba@example.com",
      bulkActionStatus: 500,
    });
    vi.stubGlobal("fetch", fetchMock);

    renderApp();
    await login("dba@example.com");
    await expandAccordionAndWaitForHeading("Incidents", "Incidents");

    fireEvent.click(screen.getByLabelText("Select incident 1"));
    fireEvent.click(screen.getByRole("button", { name: "Resolve selected" }));

    await waitFor(() => {
      expect(screen.getByText("Bulk resolve failed. Changes were rolled back.")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: "Resolve" })).toBeInTheDocument();
  });

  it("runs report request", async () => {
    const fetchMock = createFetchMock({ reportRows: [{ status: "open", total: 3 }] });
    vi.stubGlobal("fetch", fetchMock);

    renderApp();
    await login("analyst@example.com");
    await expandAccordionAndWaitForHeading("SQL Reports", "SQL reports (read-only)");

    fireEvent.click(screen.getByRole("button", { name: "Run report" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url, options]) =>
            String(url).includes("/reports/run") &&
            (options?.method || "GET").toUpperCase() === "POST",
        ),
      ).toBe(true);
    });
  });

  it("routes a natural-language query to a suggested report", async () => {
    const fetchMock = createFetchMock({
      aiFindReportResponse: {
        report_key: "incidents_by_status",
        title: "Incidents by status",
        description: "Aggregated incident status counts",
        matched_by: "llm",
        confidence: 0.92,
      },
    });
    vi.stubGlobal("fetch", fetchMock);

    renderApp();
    await login("analyst@example.com");
    await expandAccordionAndWaitForHeading("AI Operations Assist", "AI Operations Assist");

    fireEvent.change(screen.getByPlaceholderText("Example: Are there any high severity incidents still open right now?"), {
      target: { value: "Show me incident counts by status" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Find report" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url, options]) =>
            String(url).includes("/api/ai/find-report") &&
            (options?.method || "GET").toUpperCase() === "POST" &&
            String(options?.body || "").includes("Show me incident counts by status"),
        ),
      ).toBe(true);
      expect(screen.getByText(/Suggested:/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Incidents by status/i).length).toBeGreaterThan(0);
    });
  });

  it("applies the AI-suggested report to the SQL reports panel", async () => {
    vi.stubGlobal("fetch", createFetchMock());

    renderApp();
    await login("analyst@example.com");
    await expandAccordionAndWaitForHeading("AI Operations Assist", "AI Operations Assist");

    fireEvent.change(screen.getByPlaceholderText("Example: Are there any high severity incidents still open right now?"), {
      target: { value: "status counts" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Find report" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Use this report" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Use this report" }));
    await expandAccordionAndWaitForHeading("SQL Reports", "SQL reports (read-only)");

    await waitFor(() => {
      expect(screen.getByText("AI selected Incidents by status. Ready to run.")).toBeInTheDocument();
    });
  });

  it("renders incident handoff summary lines from AI endpoint", async () => {
    const fetchMock = createFetchMock({
      aiIncidentSummaryResponse: {
        incident_id: 1,
        source: "heuristic",
        summary_lines: [
          "Incident 1 is open and high severity.",
          "Most frequent workflow action is acknowledge.",
          "Recent timeline confirms owner handoff completed.",
        ],
      },
    });
    vi.stubGlobal("fetch", fetchMock);

    renderApp();
    await login("analyst@example.com");
    await expandAccordionAndWaitForHeading("AI Operations Assist", "AI Operations Assist");

    fireEvent.change(screen.getByPlaceholderText("Incident ID"), {
      target: { value: "1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Summarize incident" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url, options]) =>
            String(url).includes("/api/ai/summarize-incident/1") &&
            (options?.method || "GET").toUpperCase() === "POST",
        ),
      ).toBe(true);
      expect(screen.getByText("Incident 1 is open and high severity.")).toBeInTheDocument();
      expect(screen.getByText("Most frequent workflow action is acknowledge.")).toBeInTheDocument();
    });
  });

  it("shows incident summary API errors", async () => {
    vi.stubGlobal(
      "fetch",
      createFetchMock({
        aiIncidentSummaryStatus: 404,
        aiIncidentSummaryResponse: { detail: "Incident not found" },
      }),
    );

    renderApp();
    await login("analyst@example.com");
    await expandAccordionAndWaitForHeading("AI Operations Assist", "AI Operations Assist");

    fireEvent.change(screen.getByPlaceholderText("Incident ID"), {
      target: { value: "999" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Summarize incident" }));

    await waitFor(() => {
      expect(screen.getByText("Incident not found")).toBeInTheDocument();
    });
  });

  it("DBA can create and toggle a report schedule", async () => {
    const fetchMock = createFetchMock({ meRole: "DBA", meEmail: "dba@example.com" });
    vi.stubGlobal("fetch", fetchMock);

    renderApp();
    await login("dba@example.com");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Business Metrics (DBA)" })).toBeInTheDocument();
    });
    await expandAccordionAndWaitForHeading("Scheduled Reports (DBA)", "Scheduled reports (DBA)");
    expandAccordion("Scheduler Health (DBA)");
    expect(screen.getByText(/Create first team member/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue("starter")).toBeInTheDocument();
    expect(screen.getByText(/7 remaining/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Activity trend/i })).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Scheduler Health (DBA)" })).toBeInTheDocument();
    expect(screen.getByText(/Processed last iteration:/i)).toBeInTheDocument();

    expect(screen.getByText(/Local time preview:/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Save billing settings" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url, options]) =>
            String(url).includes("/admin/billing") &&
            (options?.method || "GET").toUpperCase() === "PUT",
        ),
      ).toBe(true);
    });

    fireEvent.click(screen.getByRole("button", { name: "Subscribe with Stripe" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url, options]) =>
            String(url).includes("/billing/checkout/session") &&
            (options?.method || "GET").toUpperCase() === "POST",
        ),
      ).toBe(true);
    });

    fireEvent.change(screen.getByDisplayValue("none"), {
      target: { value: "email" },
    });
    fireEvent.change(screen.getByPlaceholderText("ops@example.com"), {
      target: { value: "ops@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create schedule" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url, options]) =>
            String(url).includes("/reports/schedules") &&
            (options?.method || "GET").toUpperCase() === "POST",
        ),
      ).toBe(true);
    });

    fireEvent.click(screen.getByRole("button", { name: "Disable" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url, options]) =>
            String(url).includes("/reports/schedules/1/status") &&
            (options?.method || "GET").toUpperCase() === "PATCH",
        ),
      ).toBe(true);
    });
  });

  it("DBA report audit trail updates for 10, 25, all, and refresh", async () => {
    const runs = Array.from({ length: 12 }, (_, idx) => ({
      id: 201 + idx,
      created_at: `2026-05-09T${String(23 - idx).padStart(2, "0")}:00:00`,
      user_email: "dba@example.com",
      report_key: `audit-run-${idx + 1}`,
      row_count: idx + 1,
      duration_ms: 5 + idx,
      success: idx !== 11,
      error_message: idx === 11 ? "failed" : null,
    }));
    vi.stubGlobal("fetch", createFetchMock({ meRole: "DBA", meEmail: "dba@example.com", auditRuns: runs }));

    renderApp();
    await login("dba@example.com");
    await expandAccordionAndWaitForHeading("Report Audit Trail (DBA)", "Report audit trail (DBA)");

    expect(screen.getByText("audit-run-1")).toBeInTheDocument();
    expect(screen.getByText("audit-run-2")).toBeInTheDocument();
    expect(screen.getByText("audit-run-3")).toBeInTheDocument();
    expect(screen.queryByText("audit-run-4")).not.toBeInTheDocument();
    expect(screen.getByText(/Loaded 12 run\(s\) at/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Audit view"), {
      target: { value: "10" },
    });

    await waitFor(() => {
      expect(screen.getByText("audit-run-10")).toBeInTheDocument();
      expect(screen.queryByText("audit-run-11")).not.toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Audit view"), {
      target: { value: "25" },
    });

    await waitFor(() => {
      expect(screen.getByText("audit-run-12")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Audit view"), {
      target: { value: "all" },
    });

    await waitFor(() => {
      expect(screen.getByText("audit-run-12")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    await waitFor(() => {
      expect(screen.getAllByRole("row").length).toBeGreaterThan(1);
      expect(screen.getByText(/Loaded 12 run\(s\) at/)).toBeInTheDocument();
    });
  });

  it("exports report csv", async () => {
    const fetchMock = createFetchMock({ reportRows: [{ status: "open", total: 3 }] });
    vi.stubGlobal("fetch", fetchMock);
    const createObjectURL = vi.fn(() => "blob:csv");
    const revokeObjectURL = vi.fn();
    const anchorClickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const originalCreateObjectURL = URL.createObjectURL;
    const originalRevokeObjectURL = URL.revokeObjectURL;
    URL.createObjectURL = createObjectURL;
    URL.revokeObjectURL = revokeObjectURL;
    try {
      renderApp();
      await login("analyst@example.com");
      await expandAccordionAndWaitForHeading("SQL Reports", "SQL reports (read-only)");

      fireEvent.click(screen.getByRole("button", { name: "Run report" }));
      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Export CSV" })).not.toBeDisabled();
      });

      fireEvent.click(screen.getByRole("button", { name: "Export CSV" }));

      await waitFor(() => {
        expect(
          fetchMock.mock.calls.some(
            ([url, options]) =>
              String(url).includes("/reports/export/csv") &&
              (options?.method || "GET").toUpperCase() === "POST",
          ),
        ).toBe(true);
        expect(createObjectURL).toHaveBeenCalled();
        expect(anchorClickSpy).toHaveBeenCalled();
        expect(revokeObjectURL).toHaveBeenCalled();
      });
    } finally {
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
    }
  });
});