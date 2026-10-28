import assert from "node:assert/strict";
import test from "node:test";

import { chatApiUrl, requestChat } from "../lib/chat-request.mjs";

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
  assert.equal(calls[0][0], "https://api.example/api/chat/message");
  assert.equal(calls[0][1].headers["X-Correlation-ID"], correlationId);
  assert.equal(calls[0][1].headers.Authorization, undefined);
  assert.equal(
    calls[0][1].body,
    JSON.stringify({ message: "Xin chào", conversation_id: null }),
  );
});

test("chat URL supports origins, API bases and a same-origin proxy without duplicating /api", () => {
  for (const base of ["http://localhost:8000", "http://localhost:8000/", "http://localhost:8000/api", "http://localhost:8000/api/"]) {
    assert.equal(chatApiUrl(base, "/message"), "http://localhost:8000/api/chat/message");
  }
  assert.equal(chatApiUrl("/api", "/conversations"), "/api/chat/conversations");
});

test("authenticated requests preserve context and send only fields allowed by the backend", async () => {
  const controller = new AbortController();
  await requestChat("/api", {
    message: "Câu hỏi", conversation_id: "conversation-1", heritage_context: { title: "Huế" },
    scene_context: "Cổng chính", heritage_id: 10, use_rag: true,
  }, {
    accessToken: "test-token", signal: controller.signal, randomUUID: () => "request-1",
    fetchImpl: async (url, init) => {
      assert.equal(url, "/api/chat/message");
      assert.equal(init.method, "POST");
      assert.equal(init.headers.Authorization, "Bearer test-token");
      assert.equal(init.headers["X-Correlation-ID"], "request-1");
      assert.equal(init.signal, controller.signal);
      assert.deepEqual(JSON.parse(init.body), {
        message: "Câu hỏi", conversation_id: "conversation-1", heritage_context: { title: "Huế" },
        scene_context: "Cổng chính", heritage_id: 10,
      });
      return new Response("{}", { status: 201 });
    },
  });
});

test("guest requests forward completed bounded conversation context", async () => {
  const history = [
    { role: "user", content: "Which heritage is this?" },
    { role: "assistant", content: "This is the current heritage." },
  ];
  await requestChat("/api", { message: "When was it built?", conversation_context: history }, {
    randomUUID: () => "guest-request",
    fetchImpl: async (_url, init) => {
      assert.deepEqual(JSON.parse(init.body), {
        message: "When was it built?", conversation_id: null, conversation_context: history,
      });
      assert.equal(init.headers.Authorization, undefined);
      return new Response("{}", { status: 201 });
    },
  });
});
