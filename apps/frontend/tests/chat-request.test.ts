import assert from "node:assert/strict";
import test from "node:test";

import { requestChat } from "../lib/chat-request";

test("chat request sends a generated correlation ID", async () => {
  const calls: unknown[][] = [];
  const response = { json: async () => ({ answer: "ok" }) } as unknown as Response;
  const correlationId = "123e4567-e89b-12d3-a456-426614174000";

  const result = await requestChat("https://api.example", "Xin chào", {
    fetchImpl: async (...args: unknown[]) => {
      calls.push(args);
      return response;
    },
    randomUUID: () => correlationId,
  });

  assert.equal(result, response);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "https://api.example/api/chat");
  const options = calls[0][1] as { headers: Record<string, string>; body: string };
  assert.equal(options.headers["X-Correlation-ID"], correlationId);
  assert.equal(
    options.body,
    JSON.stringify({ message: "Xin chào", use_rag: true }),
  );
});
