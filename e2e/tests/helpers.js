// Shared steps for the core-flow specs (ported from the May suite, PR #3).
export const API_URL = "http://localhost:8000"; // the build's fallback when VITE_API_URL is unset (as in CI)
export const DBA_EMAIL = "dba@example.com";
export const DBA_PASSWORD = "Password123!";

// Signed-out visitors land on the marketing page; "Sign In" opens the app's login panel.
export async function openLogin(page) {
  await page.goto("/");
  const signIn = page.getByText("Sign In", { exact: true }).first();
  if (await signIn.isVisible().catch(() => false)) await signIn.click();
}

export async function mockAuth(page, { email = DBA_EMAIL, role = "DBA" } = {}) {
  await page.route(`${API_URL}/auth/login`, async (route) => {
    const body = route.request().postDataJSON() || {};
    if (body.email === email && body.password === DBA_PASSWORD) {
      await route.fulfill({ status: 200, contentType: "application/json",
        body: JSON.stringify({ access_token: "fake-token", token_type: "bearer" }) });
    } else {
      await route.fulfill({ status: 401, contentType: "application/json",
        body: JSON.stringify({ detail: "Invalid credentials" }) });
    }
  });
  await page.route(`${API_URL}/auth/me`, (route) => route.fulfill({ status: 200, contentType: "application/json",
    body: JSON.stringify({ id: 1, email, role, display_name: "DBA User", is_active: true }) }));
}

export async function login(page, email = DBA_EMAIL, password = DBA_PASSWORD) {
  await page.getByPlaceholder("Email", { exact: true }).fill(email);
  await page.getByPlaceholder("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Login", exact: true }).click();
}
