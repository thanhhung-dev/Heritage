import assert from "node:assert/strict";
import test from "node:test";
import {
  readConversationId,
  saveConversationId,
  requestConversationHistory,
} from "../lib/conversation-storage";

const id = "11111111-1111-4111-8111-111111111111";

function storage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  };
}

test("saved conversation pointers are separated by account and tour, and guests never reuse them", () => {
  const store = storage();
  saveConversationId(store, "A", "tour:khiem-lang", id);
  assert.equal(readConversationId(store, "A", "tour:khiem-lang"), id);
  assert.equal(readConversationId(store, "B", "tour:khiem-lang"), null);
  assert.equal(readConversationId(store, "A", "standalone"), null);
  assert.equal(readConversationId(store, null, "tour:khiem-lang"), null);
  saveConversationId(store, "A", "tour:khiem-lang", null);
  assert.equal(readConversationId(store, "A", "tour:khiem-lang"), null);
});

test("unavailable browser storage does not break in-memory chat", () => {
  const blocked = {
    getItem() {
      throw Error("blocked");
    },
    setItem() {
      throw Error("blocked");
    },
    removeItem() {
      throw Error("blocked");
    },
  };
  assert.equal(readConversationId(blocked, "A", "standalone"), null);
  assert.doesNotThrow(() => saveConversationId(blocked, "A", "standalone", id));
});

test("history management always uses JWT and the exact owned API routes", async () => {
  const calls: unknown[][] = [];
  const options = {
    accessToken: "test-token",
    fetchImpl: (async (...args: unknown[]) => {
      calls.push(args);
      return { ok: true } as Response;
    }) as typeof fetch,
  };

  await requestConversationHistory("https://example.test/api", { limit: 50, offset: 5 }, options);
  await requestConversationHistory("https://example.test/api", { id }, options);
  await requestConversationHistory("https://example.test/api", { id, method: "DELETE" }, options);

  assert.equal(calls[0][0], "https://example.test/api/chat/conversations?limit=50&offset=5");
  assert.equal(calls[1][0], `https://example.test/api/chat/conversations/${id}/messages`);
  assert.equal(calls[2][0], `https://example.test/api/chat/conversations/${id}`);
  const thirdInit = calls[2][1] as { method: string };
  assert.equal(thirdInit.method, "DELETE");

  assert.ok(
    calls.every(([, init]) => (init as { headers: Record<string, string> }).headers.Authorization === "Bearer test-token"),
  );
  assert.throws(() => requestConversationHistory("/api", { id }), /đăng nhập/);
  assert.throws(() => requestConversationHistory("/api", { id: "../other" }, options), /không hợp lệ/);
});
