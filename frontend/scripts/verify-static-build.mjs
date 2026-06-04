/**
 * Ensures production dist is a built Vite app (not dev index.html).
 * Run after `npm run build` — wired as postbuild and in CI.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const distDir = path.join(root, "dist");
const indexPath = path.join(distDir, "index.html");

function fail(message) {
  console.error(`verify-static-build: ${message}`);
  process.exit(1);
}

if (!fs.existsSync(indexPath)) {
  fail("dist/index.html missing — run vite build");
}

const html = fs.readFileSync(indexPath, "utf8");

if (
  /type="module"[^>]*\ssrc="\/src\/main\.jsx"/.test(html) ||
  /src="\/src\/main\.jsx"[^>]*type="module"/.test(html)
) {
  fail("dist/index.html still loads /src/main.jsx (dev template). Check Render staticPublishPath=dist and buildCommand.");
}

const scriptMatch = html.match(/src="(\/assets\/[^"]+\.js)"/);
if (!scriptMatch) {
  fail("dist/index.html has no /assets/*.js script tag — build output is incomplete.");
}

const assetRel = scriptMatch[1].replace(/^\//, "");
const assetPath = path.join(distDir, assetRel);
if (!fs.existsSync(assetPath)) {
  fail(`referenced bundle missing: dist/${assetRel}`);
}

const assetsDir = path.join(distDir, "assets");
if (!fs.existsSync(assetsDir)) {
  fail("dist/assets/ directory missing");
}

console.log("verify-static-build: OK", scriptMatch[1]);
