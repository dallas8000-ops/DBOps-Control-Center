import { render } from "@testing-library/react";

import App from "../App";

/** Render App without React StrictMode (avoids double-effect noise in smoke tests). */
export function renderApp(options = {}) {
  return render(<App />, options);
}
