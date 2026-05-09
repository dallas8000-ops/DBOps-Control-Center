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

function createFetchMock({
  meRole = "Analyst",
  meEmail = "analyst@example.com",
  reportRows = [{ status: "open", total: 1 }],
} = {}) {
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
    "GET /reports/runs": jsonResponse([]),
    "GET /auth/users": jsonResponse([]),
  };

  return vi.fn(async (url, options = {}) => {
    const method = (options.method || "GET").toUpperCase();
    const path = new URL(String(url)).pathname;
    const key = routeKey(method, path);
    if (staticResponses[key]) return staticResponses[key];

    if (path === "/auth/login" && method === "POST") {
      return jsonResponse({ access_token: "token-123", token_type: "bearer" });
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
});

afterEach(() => {
  cleanup();
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