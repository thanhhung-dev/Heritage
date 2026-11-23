import assert from "node:assert/strict";
import test from "node:test";
import { setAuthTokens } from "../lib/auth";

const session = { access_token: "synthetic-new-token", token_type: "bearer",
  user: { account_id: "7", email: "test@example.com", username: "test_user", role: "user" } };

test("saving authentication updates both fields before notifying consumers", () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  const values = new Map<string, string>(); let notifications = 0;
  Object.defineProperty(globalThis, "window", { configurable: true, value: {
    localStorage: { getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value), removeItem: (key: string) => values.delete(key) },
    dispatchEvent: () => { assert.equal(values.get("heritage_access_token"), session.access_token); assert.ok(values.get("heritage_user")); notifications++; },
  } });
  try { setAuthTokens(session); assert.equal(notifications, 1); }
  finally { if (previous) Object.defineProperty(globalThis, "window", previous); else Reflect.deleteProperty(globalThis, "window"); }
});

test("failed token storage rolls back the user field and never announces a partial session", () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  const values = new Map([['heritage_access_token', 'previous-token'], ['heritage_user', 'previous-user']]);
  let fail = true, notifications = 0;
  Object.defineProperty(globalThis, "window", { configurable: true, value: {
    localStorage: { getItem: (key: string) => values.get(key) ?? null, removeItem: (key: string) => values.delete(key),
      setItem: (key: string, value: string) => { if (key === 'heritage_access_token' && fail) { fail = false; throw new Error('Quota exceeded'); } values.set(key, value); } },
    dispatchEvent: () => { notifications++; },
  } });
  try {
    assert.throws(() => setAuthTokens(session), /Quota exceeded/);
    assert.deepEqual([...values], [['heritage_access_token', 'previous-token'], ['heritage_user', 'previous-user']]);
    assert.equal(notifications, 0);
  } finally { if (previous) Object.defineProperty(globalThis, "window", previous); else Reflect.deleteProperty(globalThis, "window"); }
});
