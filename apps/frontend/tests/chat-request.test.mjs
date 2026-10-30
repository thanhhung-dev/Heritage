import assert from "node:assert/strict";
import test from "node:test";

import { requestChat } from "../lib/chat-request.mjs";

test("chat request sends a generated correlation ID", async () => {
  const calls = [];
  const response = { json: async () => ({ answer: "ok" }) };
  const correlationId = "123e4567-e89b-12d3-a456-426614174000";

  const result = await requestChat("https://api.example", "Xin chào", {
    fetchImpl: async (...args) => {
      calls.push(args);
      return response;
    },
    randomUUID: () => correlationId,
  });

  assert.equal(result, response);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "https://api.example/api/chat");
  assert.equal(calls[0][1].headers["X-Correlation-ID"], correlationId);
  assert.equal(
    calls[0][1].body,
    JSON.stringify({ message: "Xin chào", use_rag: true }),
  );
});

test("chat accepts an API origin, /api base and same-origin proxy without duplicating the prefix", async () => {
  for (const [base, expected] of [["http://localhost:8000", "http://localhost:8000/api/chat"],
    ["http://localhost:8000/api/", "http://localhost:8000/api/chat"], ["/api", "/api/chat"]]) {
    await requestChat(base, "Question", { randomUUID: () => "qa", fetchImpl: async (url) => { assert.equal(url, expected); return Response.json({ answer: "ok" }); } });
  }
});

test("overlay transport adds optional auth and forwards cancellation with the current backend contract", async () => {
  const controller = new AbortController();
  await requestChat("http://localhost:8000/api", "Heritage question", {
    accessToken: "access-token", signal: controller.signal, randomUUID: () => "qa",
    fetchImpl: async (_url, options) => {
      assert.equal(options.headers.Authorization, "Bearer access-token");
      assert.equal(options.signal, controller.signal);
      assert.deepEqual(JSON.parse(options.body), { message: "Heritage question", use_rag: true });
      return Response.json({ answer: "ok" });
    },
  });
});

test("Guest chat does not send an Authorization header", async () => {
  await requestChat("http://localhost:8000", "Guest question", { randomUUID: () => "qa", accessToken: null,
    fetchImpl: async (_url, options) => { assert.equal(options.headers.Authorization, undefined); return Response.json({ answer: "ok" }); },
  });
});
