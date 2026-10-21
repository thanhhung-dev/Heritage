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
