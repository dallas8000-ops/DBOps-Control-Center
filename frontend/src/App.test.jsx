import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

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

function createFetchMock({
  meRole = "Analyst",
  meEmail = "analyst@example.com",
  reportRows = [{ status: "open", total: 1 }],
  auditRuns = [],
  loginResponse = jsonResponse({ access_token: "token-123", token_type: "bearer" }),
} = {}) {
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
  };

  return vi.fn(async (url, options = {}) => {
    const method = (options.method || "GET").toUpperCase();
    const path = new URL(String(url)).pathname;
    const key = routeKey(method, path);
    if (staticResponses[key]) return staticResponses[key];

    if (path === "/auth/login" && method === "POST") {
      return loginResponse;
    }

    if (path === "/incidents" && method === "GET") {
      return jsonResponse([
        {
          id: 1,
          title: "Replication lag",
          description: "Lag exceeded threshold",
          severity: "high",
          owner: "ops",
          status: "open",
          created_at: "2026-05-08T10:00:00",
        },
      ]);
    }

    if (path === "/incidents" && method === "POST") {
      return jsonResponse(
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
      );
    }

    if (path === "/reports/run" && method === "POST") {
      return jsonResponse({
        report_key: "incidents_by_status",
        columns: ["status", "total"],
        rows: reportRows,
        row_count: reportRows.length,
        truncated: false,
        duration_ms: 7,
      });
    }

    if (path === "/reports/export/csv" && method === "POST") {
      return {
        ok: true,
        status: 200,
        text: async () => "status,incident_count\nopen,1\n",
      };
    }

    if (path === "/reports/schedules" && method === "POST") {
      return jsonResponse(
        {
          ...schedules[0],
          id: 2,
          delivery_kind: "email",
          delivery_target: "ops@example.com",
        },
        201,
      );
    }

    if (path.startsWith("/reports/schedules/") && path.endsWith("/status") && method === "PATCH") {
      return jsonResponse({ ...schedules[0], is_enabled: false });
    }

    if (path.endsWith("/resolve") && method === "PATCH") {
      return jsonResponse({
        id: 1,
        title: "Replication lag",
        description: "Lag exceeded threshold",
        severity: "high",
        owner: "ops",
        status: "resolved",
        created_at: "2026-05-08T10:00:00",
      });
    }

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
  vi.restoreAllMocks();
});

describe("App smoke", () => {
  it("renders login panel", () => {
    vi.stubGlobal("fetch", createFetchMock());
    render(<App />);
    expect(screen.getByRole("heading", { name: "DBOps Control Center" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Login" })).toBeInTheDocument();
  });

  it("logs in and shows signed-in header", async () => {
    vi.stubGlobal("fetch", createFetchMock());

    render(<App />);

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

    render(<App />);

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

    render(<App />);

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

    render(<App />);

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

    render(<App />);

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

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Your session expired. Please sign in again.")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Login" })).toBeInTheDocument();
    expect(globalThis.window.localStorage.getItem("dbops_token")).toBeNull();
  });

  it("submits create incident request", async () => {
    const fetchMock = createFetchMock();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.change(screen.getByPlaceholderText("Email"), {
      target: { value: "analyst@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Create Incident" })).toBeInTheDocument();
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

  it("runs report request", async () => {
    const fetchMock = createFetchMock({ reportRows: [{ status: "open", total: 3 }] });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.change(screen.getByPlaceholderText("Email"), {
      target: { value: "analyst@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "SQL reports (read-only)" })).toBeInTheDocument();
    });

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

  it("DBA can create and toggle a report schedule", async () => {
    const fetchMock = createFetchMock({ meRole: "DBA", meEmail: "dba@example.com" });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.change(screen.getByPlaceholderText("Email"), {
      target: { value: "dba@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Scheduled reports (DBA)" })).toBeInTheDocument();
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

  it("DBA report audit trail defaults to last 3 and can show all", async () => {
    const runs = [
      { id: 201, created_at: "2026-05-09T10:00:00", user_email: "dba@example.com", report_key: "audit-run-1", row_count: 2, duration_ms: 7, success: true, error_message: null },
      { id: 202, created_at: "2026-05-09T09:00:00", user_email: "dba@example.com", report_key: "audit-run-2", row_count: 3, duration_ms: 8, success: true, error_message: null },
      { id: 203, created_at: "2026-05-09T08:00:00", user_email: "dba@example.com", report_key: "audit-run-3", row_count: 1, duration_ms: 5, success: true, error_message: null },
      { id: 204, created_at: "2026-05-09T07:00:00", user_email: "dba@example.com", report_key: "audit-run-4", row_count: null, duration_ms: null, success: false, error_message: "failed" },
    ];
    vi.stubGlobal("fetch", createFetchMock({ meRole: "DBA", meEmail: "dba@example.com", auditRuns: runs }));

    render(<App />);

    fireEvent.change(screen.getByPlaceholderText("Email"), {
      target: { value: "dba@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Report audit trail (DBA)" })).toBeInTheDocument();
    });

    expect(screen.getByText("audit-run-1")).toBeInTheDocument();
    expect(screen.getByText("audit-run-2")).toBeInTheDocument();
    expect(screen.getByText("audit-run-3")).toBeInTheDocument();
    expect(screen.queryByText("audit-run-4")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Audit view"), {
      target: { value: "all" },
    });

    await waitFor(() => {
      expect(screen.getByText("audit-run-4")).toBeInTheDocument();
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
      render(<App />);

      fireEvent.change(screen.getByPlaceholderText("Email"), {
        target: { value: "analyst@example.com" },
      });
      fireEvent.change(screen.getByPlaceholderText("Password"), {
        target: { value: "Password123!" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Login" }));

      await waitFor(() => {
        expect(screen.getByRole("heading", { name: "SQL reports (read-only)" })).toBeInTheDocument();
      });

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