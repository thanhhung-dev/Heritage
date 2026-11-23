import assert from "node:assert/strict";
import test from "node:test";
import { AuthApiError, authResponseError, createAuthApi } from "../services/auth-api";
import { passwordError, usernameError, safeAuthNext, registrationSignInHref } from "../features/auth/auth-validation";

test("registration policy matches backend while login allows legacy passwords", () => {
  assert.match(passwordError("1234567", true), /at least 8/);
  assert.equal(passwordError("12345678", true), "");
  assert.equal(passwordError("old", false), "");
  assert.match(passwordError("        ", true), /only spaces/);
  assert.match(usernameError("a".repeat(51)), /3 and 50/);
  assert.equal(usernameError("  khoa_đà-nẵng  "), "");
});

test("FastAPI validation arrays and structured errors never stringify objects or expose inputs", () => {
  const error = authResponseError({ detail: [{ loc: ["body", "password"], msg: "String should have at least 8 characters", input: "private" },
    { loc: ["body", "email"], msg: "Invalid email" }] }, 422);
  assert.equal(error.fields.password, "String should have at least 8 characters");
  assert.match(error.message, /Password:/); assert.doesNotMatch(error.message, /object Object|private/);
  assert.equal(authResponseError({ detail: { message: "Account locked" } }, 403).message, "Account locked");
  assert.match(authResponseError({ detail: { code: "unknown" } }, 503).message, /temporarily unavailable/);
  assert.match(authResponseError(null, 429).message, /Too many/);
});

test("auth requests normalize identity, preserve password and surface HTTP and non-JSON failures", async () => {
  const requests: unknown[] = [];
  const api = createAuthApi({ baseUrl: "https://api.example.invalid/api/", fetchImpl: async (url, options) => {
    requests.push([url, JSON.parse(String(options?.body))]);
    return Response.json({ account_id: 12, email: "khoa@example.com", username: "khoa", message: "Created" });
  } });
  assert.equal((await api.register({ email: " Khoa@Example.com ", username: " khoa ", password: " exact password " })).account_id, "12");
  assert.deepEqual(requests, [["https://api.example.invalid/api/auth/register", { email: "khoa@example.com", username: "khoa", password: " exact password " }]]);
  for (const [body, status, expected] of [[{ detail: "Email already in use" }, 400, /already in use/], ["gateway html", 502, /temporarily unavailable/]] as const) {
    const failing = createAuthApi({ fetchImpl: async () => new Response(typeof body === "string" ? body : JSON.stringify(body), { status }) });
    await assert.rejects(failing.login({ email: "a@example.com", password: "x" }), expected);
  }
});

test("network/timeout errors are actionable and malformed success never creates a session", async () => {
  const network = createAuthApi({ fetchImpl: async () => { throw new TypeError("fetch failed"); } });
  await assert.rejects(network.login({ email: "a@example.com", password: "x" }), /Cannot connect/);
  const timeout = createAuthApi({ timeoutMs: 1, fetchImpl: async (_url, options) => new Promise((_resolve, reject) => {
    options?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
  }) });
  await assert.rejects(timeout.login({ email: "a@example.com", password: "x" }), /timed out/);
  const malformed = createAuthApi({ fetchImpl: async () => Response.json({ access_token: "", user: {} }) });
  await assert.rejects(malformed.login({ email: "a@example.com", password: "x" }), (error: unknown) => error instanceof AuthApiError && error.status === 502);
});

test("post-login redirects retain local destinations and reject external/auth-loop paths", () => {
  for (const value of ["https://evil.invalid", "//evil.invalid", "/\\evil.invalid", "/sign-in?next=/", "/\n/evil.invalid"]) assert.equal(safeAuthNext(value), "/");
  assert.equal(safeAuthNext("/admin/documents?prefix=archives%2F"), "/admin/documents?prefix=archives%2F");
  assert.equal(registrationSignInHref("/admin/documents"), "/sign-in?registered=1&next=%2Fadmin%2Fdocuments");
});
