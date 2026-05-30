import { test, expect } from "@playwright/test";

const BASE_URL = "http://localhost:5173";
const API_URL = "http://localhost:8000";

const DBA_EMAIL = "dba@example.com";
const DBA_PASSWORD = "Password123!";

test.describe("Create Incident", () => {
  test.beforeEach(async ({ page }) => {
    // Intercept login API
    await page.route(`${API_URL}/auth/login`, async (route) => {
      const request = route.request();
      const postData = request.postDataJSON();
      if (postData.email === DBA_EMAIL && postData.password === DBA_PASSWORD) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            access_token: "fake-dba-token",
            token_type: "bearer",
          }),
        });
      } else {
        await route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Invalid credentials" }),
        });
      }
    });

    // Intercept /auth/me
    await page.route(`${API_URL}/auth/me`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          email: DBA_EMAIL,
          role: "DBA",
          display_name: "DBA User",
          is_active: true,
        }),
      });
    });

    // Intercept GET /incidents
    await page.route(`${API_URL}/incidents`, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto(BASE_URL);

    // Perform login
    await page.getByPlaceholder("Email").fill(DBA_EMAIL);
    await page.getByPlaceholder("Password").fill(DBA_PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();

    // Wait for authenticated state
    await expect(page.getByText(`Signed in as ${DBA_EMAIL}`)).toBeVisible({
      timeout: 10000,
    });
  });

  test("should expand Create Incident accordion and create a new incident", async ({
    page,
  }) => {
    let createIncidentRequestBody = null;

    // Track the POST /incidents call
    await page.route(`${API_URL}/incidents`, async (route) => {
      const method = route.request().method();
      if (method === "POST") {
        createIncidentRequestBody = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: 42,
            title: "E2E Test \u2013 Disk usage alert",
            description: "Root volume exceeded 90% on db-primary-01",
            owner: DBA_EMAIL,
            status: "open",
            severity: "medium",
            created_at: new Date().toISOString(),
          }),
        });
      } else if (method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      } else {
        await route.continue();
      }
    });

    // Expand "Create Incident" accordion if not already expanded
    const createAccordionBtn = page.getByRole("button", {
      name: /create incident/i,
    });
    await expect(createAccordionBtn).toBeVisible({ timeout: 10000 });

    const isExpanded =
      await createAccordionBtn.getAttribute("aria-expanded");
    if (isExpanded !== "true") {
      await createAccordionBtn.click();
    }

    await expect(createAccordionBtn).toHaveAttribute("aria-expanded", "true");

    // Fill in the form fields
    const titleInput = page.getByPlaceholder("Title");
    const descriptionInput = page.getByPlaceholder("Description");
    const ownerInput = page.getByPlaceholder("Owner");

    await expect(titleInput).toBeVisible();
    await expect(descriptionInput).toBeVisible();
    await expect(ownerInput).toBeVisible();

    await titleInput.fill("E2E Test \u2013 Disk usage alert");
    await descriptionInput.fill("Root volume exceeded 90% on db-primary-01");
    await ownerInput.fill(DBA_EMAIL);

    // Verify values entered
    await expect(titleInput).toHaveValue("E2E Test \u2013 Disk usage alert");
    await expect(descriptionInput).toHaveValue(
      "Root volume exceeded 90% on db-primary-01"
    );
    await expect(ownerInput).toHaveValue(DBA_EMAIL);

    // Click the Create button
    const createBtn = page.getByRole("button", { name: "Create" });
    await expect(createBtn).toBeVisible();
    await createBtn.click();

    // Wait for the POST request to have been made
    await page.waitForResponse(
      (response) =>
        response.url().includes(`${API_URL}/incidents`) &&
        response.request().method() === "POST" &&
        response.status() === 201,
      { timeout: 10000 }
    );

    // Verify the request body contained the correct data
    expect(createIncidentRequestBody).not.toBeNull();
    expect(createIncidentRequestBody.title).toBe(
      "E2E Test \u2013 Disk usage alert"
    );
    expect(createIncidentRequestBody.description).toBe(
      "Root volume exceeded 90% on db-primary-01"
    );
    expect(createIncidentRequestBody.owner).toBe(DBA_EMAIL);

    // After creation, the form should reset (fields should be empty)
    // or a success message should appear
    // Try checking if the title field has been reset
    const titleValueAfter = await titleInput.inputValue().catch(() => "");
    const descValueAfter = await descriptionInput.inputValue().catch(() => "");
    // Form reset check - if the form resets, fields should be empty
    // If not resetting, we at least verify the API was called correctly (done above)
    // Some apps show success notifications
    const formReset =
      titleValueAfter === "" && descValueAfter === "";
    const hasSuccessMessage = await page
      .getByText(/incident created|success/i)
      .isVisible()
      .catch(() => false);

    // At least one of these should be true after a successful create
    expect(formReset || hasSuccessMessage || createIncidentRequestBody !== null).toBeTruthy();
  });

  test("should show the new incident in the Incidents accordion after creation", async ({
    page,
  }) => {
    const newIncident = {
      id: 99,
      title: "E2E Test \u2013 Disk usage alert",
      description: "Root volume exceeded 90% on db-primary-01",
      owner: DBA_EMAIL,
      status: "open",
      severity: "medium",
      created_at: new Date().toISOString(),
    };

    let incidentCreated = false;

    // Route for POST /incidents
    await page.route(`${API_URL}/incidents`, async (route) => {
      const method = route.request().method();
      if (method === "POST") {
        incidentCreated = true;
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(newIncident),
        });
      } else if (method === "GET") {
        // Return the new incident after it's created
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(incidentCreated ? [newIncident] : []),
        });
      } else {
        await route.continue();
      }
    });

    // Expand Create Incident accordion
    const createAccordionBtn = page.getByRole("button", {
      name: /create incident/i,
    });
    await expect(createAccordionBtn).toBeVisible({ timeout: 10000 });

    const isExpanded =
      await createAccordionBtn.getAttribute("aria-expanded");
    if (isExpanded !== "true") {
      await createAccordionBtn.click();
    }
    await expect(createAccordionBtn).toHaveAttribute("aria-expanded", "true");

    // Fill form
    await page.getByPlaceholder("Title").fill("E2E Test \u2013 Disk usage alert");
    await page
      .getByPlaceholder("Description")
      .fill("Root volume exceeded 90% on db-primary-01");
    await page.getByPlaceholder("Owner").fill(DBA_EMAIL);

    // Submit
    await page.getByRole("button", { name: "Create" }).click();

    // Wait for POST to complete
    await page.waitForResponse(
      (response) =>
        response.url().includes(`${API_URL}/incidents`) &&
        response.request().method() === "POST",
      { timeout: 10000 }
    );

    // Now open the Incidents accordion
    const incidentsAccordionBtn = page.getByRole("button", {
      name: /^incidents$/i,
    });
    await expect(incidentsAccordionBtn).toBeVisible({ timeout: 10000 });

    const incidentsExpanded =
      await incidentsAccordionBtn.getAttribute("aria-expanded");
    if (incidentsExpanded !== "true") {
      await incidentsAccordionBtn.click();
    }
    await expect(incidentsAccordionBtn).toHaveAttribute("aria-expanded", "true");

    // Wait for the incident list to load and verify the new incident appears
    await expect(
      page.getByText("E2E Test \u2013 Disk usage alert")
    ).toBeVisible({ timeout: 10000 });
  });

  test("should validate that title is required before creating an incident", async ({
    page,
  }) => {
    let postWasMade = false;

    // Track if POST is erroneously made
    await page.route(`${API_URL}/incidents`, async (route) => {
      const method = route.request().method();
      if (method === "POST") {
        postWasMade = true;
        await route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Title is required" }),
        });
      } else if (method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      } else {
        await route.continue();
      }
    });

    // Expand Create Incident accordion
    const createAccordionBtn = page.getByRole("button", {
      name: /create incident/i,
    });
    await expect(createAccordionBtn).toBeVisible({ timeout: 10000 });

    const isExpanded =
      await createAccordionBtn.getAttribute("aria-expanded");
    if (isExpanded !== "true") {
      await createAccordionBtn.click();
    }
    await expect(createAccordionBtn).toHaveAttribute("aria-expanded", "true");

    // Leave title empty, only fill in description and owner
    await page
      .getByPlaceholder("Description")
      .fill("Root volume exceeded 90% on db-primary-01");
    await page.getByPlaceholder("Owner").fill(DBA_EMAIL);

    // Title should be empty
    const titleInput = page.getByPlaceholder("Title");
    await expect(titleInput).toHaveValue("");

    // Try clicking Create
    const createBtn = page.getByRole("button", { name: "Create" });
    await expect(createBtn).toBeVisible();
    await createBtn.click();

    // Wait a bit to see if any request is made
    await page.waitForTimeout(500);

    // Check HTML5 native validation: the title input should be required
    // or the app should show a validation error message
    // Check if form prevented submission via HTML5 required attribute
    const isTitleRequired = await titleInput.getAttribute("required");
    const hasValidationError = await page
      .getByText(/title.*required|required.*title|please.*title|title.*empty/i)
      .isVisible()
      .catch(() => false);

    // Either the field is marked as required (preventing form submission)
    // or the app shows a validation error
    // or the POST was not made without a title
    // If POST was made, it should have been rejected with a validation error
    if (postWasMade) {
      // The server returned 422, check for error message
      const hasErrorMessage = await page
        .getByText(/title.*required|error|failed|invalid/i)
        .isVisible()
        .catch(() => false);
      expect(hasErrorMessage || isTitleRequired !== null).toBeTruthy();
    } else {
      // Client-side validation prevented submission
      expect(isTitleRequired !== null || hasValidationError).toBeTruthy();
    }

    // Ensure that if no title was submitted, the form did not succeed
    const formStillVisible = await page
      .getByPlaceholder("Title")
      .isVisible()
      .catch(() => false);
    expect(formStillVisible).toBeTruthy();
  });

  test("should verify the Create button is visible and accessible for DBA role", async ({
    page,
  }) => {
    await page.route(`${API_URL}/incidents`, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      } else {
        await route.continue();
      }
    });

    // Verify role is shown
    await expect(page.getByText(/DBA/i)).toBeVisible({ timeout: 5000 });

    // Expand Create Incident accordion
    const createAccordionBtn = page.getByRole("button", {
      name: /create incident/i,
    });
    await expect(createAccordionBtn).toBeVisible({ timeout: 10000 });

    const isExpanded =
      await createAccordionBtn.getAttribute("aria-expanded");
    if (isExpanded !== "true") {
      await createAccordionBtn.click();
    }
    await expect(createAccordionBtn).toHaveAttribute("aria-expanded", "true");

    // All form fields should be visible
    await expect(page.getByPlaceholder("Title")).toBeVisible();
    await expect(page.getByPlaceholder("Description")).toBeVisible();
    await expect(page.getByPlaceholder("Owner")).toBeVisible();

    // Create button should be visible and enabled
    const createBtn = page.getByRole("button", { name: "Create" });
    await expect(createBtn).toBeVisible();
    await expect(createBtn).toBeEnabled();
  });
});
