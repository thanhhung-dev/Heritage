/**
 * Mock heritage API server — chạy ngoài, KHÔNG cần DB / backend Docker.
 *
 * Doc: apps/frontend/mocks/heritage-mock.json (30 địa điểm, đúng shape HeritageOut).
 *
 * Chạy:
 *   node apps/frontend/mocks/mock-server.mjs            # mặc định cổng 8001
 *   MOCK_API_PORT=9999 node apps/frontend/mocks/mock-server.mjs
 *
 * FE trỏ API sang đây:
 *   apps/frontend/.env.local  →  NEXT_PUBLIC_API_URL=http://localhost:8001/api
 *
 * Endpoints:
 *   GET /api/heritages            → array (30 items)
 *   GET /api/heritages/:slug      → 1 item hoặc 404
 *   GET /api/health               → {status:"ok", ...}
 */
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.MOCK_API_PORT || 8001);
const DELAY_MS = Number(process.env.MOCK_API_DELAY_MS || 150);

const items = JSON.parse(
  readFileSync(join(__dirname, "heritage-mock.json"), "utf-8"),
);

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Correlation-ID",
};

function send(res, status, body) {
  const json = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(json),
    ...CORS_HEADERS,
  });
  res.end(json);
}

function handle(req, res) {
  const { pathname } = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  if (req.method === "OPTIONS") {
    res.writeHead(204, CORS_HEADERS);
    return res.end();
  }

  if (req.method !== "GET") {
    return send(res, 405, { detail: "Method not allowed" });
  }

  if (pathname === "/api/health") {
    return send(res, 200, { status: "ok", inference_backend: "mock", model_ready: true });
  }

  if (pathname === "/api/heritages" || pathname === "/api/heritages/") {
    const url = new URL(req.url, "http://localhost");
    const region = (url.searchParams.get("region") || "").toLowerCase();
    const limit = Number(url.searchParams.get("limit") || items.length);
    let result = items;
    if (region) {
      result = result.filter((it) => (it.region || "").toLowerCase().includes(region));
    }
    result = result.slice(0, limit);
    // Trim to the HeritageOut shape used by the homepage list.
    return send(res, 200, result.map(({ heritage, scenes, ...it }) => it));
  }

  const match = pathname.match(/^\/api\/heritages\/([^/]+)$/);
  if (match) {
    const slug = decodeURIComponent(match[1]);
    const item = items.find((it) => it.slug === slug);
    if (!item) {
      return send(res, 404, { detail: "Heritage not found" });
    }
    // Full single-load payload: heritage object + full scenes array.
    return send(res, 200, { heritage: item, scenes: item.scenes || [] });
  }

  if (pathname === "/") {
    return send(res, 200, { name: "Heritage Mock API", items: items.length, endpoints: ["/api/health", "/api/heritages", "/api/heritages/:slug"] });
  }

  return send(res, 404, { detail: "Not found" });
}

const server = createServer((req, res) => {
  setTimeout(() => handle(req, res), DELAY_MS);
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`Mock heritage API running on http://localhost:${PORT}`);
  console.log(`  GET http://localhost:${PORT}/api/heritages  (${items.length} items)`);
});