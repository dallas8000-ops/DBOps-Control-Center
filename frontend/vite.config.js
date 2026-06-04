import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

/** Post-build guard: dist must ship hashed bundles, not dev /src/main.jsx. */
function verifyStaticBuildPlugin() {
  return {
    name: "verify-static-build",
    closeBundle() {
      const indexPath = path.join(frontendRoot, "dist", "index.html");
      const html = fs.readFileSync(indexPath, "utf8");
      if (/type="module"[^>]*\ssrc="\/src\/main\.jsx"/.test(html) || /src="\/src\/main\.jsx"[^>]*type="module"/.test(html)) {
        throw new Error("dist/index.html still loads /src/main.jsx — static deploy would show a blank page.");
      }
      if (!/\/assets\/[^"']+\.js/.test(html)) {
        throw new Error("dist/index.html has no /assets/*.js bundle — static deploy would show a blank page.");
      }
    },
  };
}

/** Some static hosts mishandle module scripts with crossorigin; same-origin Render does not need it. */
function stripCrossoriginPlugin() {
  return {
    name: "strip-crossorigin-static",
    transformIndexHtml: {
      order: "post",
      handler(html) {
        return html
          .replace(/\s+crossorigin(?:="[^"]*")?/g, "")
          .replace(/<link([^>]*)\scrossorigin(?:="[^"]*")?/g, "<link$1");
      },
    },
  };
}

export default defineConfig({
  plugins: [react(), stripCrossoriginPlugin(), verifyStaticBuildPlugin()],
});
