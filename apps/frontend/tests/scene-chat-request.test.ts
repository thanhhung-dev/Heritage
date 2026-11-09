import assert from "node:assert/strict";
import test from "node:test";

import { chatApiUrl } from "../lib/chat-request";
import {
  createConversationContext,
  requestSceneChat,
} from "../lib/scene-chat-request";

test("chat API URL does not duplicate an existing /api prefix", () => {
  assert.equal(
    chatApiUrl("https://api.example/api/", "/chat"),
    "https://api.example/api/chat",
  );
  assert.equal(
    chatApiUrl("https://api.example/", "/chat"),
    "https://api.example/api/chat",
  );
});

test("scene chat sends structured heritage and scene context", async () => {
  const calls: unknown[][] = [];
  const request = {
    message: "What should I notice here?",
    heritage_id: 42,
    heritage_context: { id: 42, slug: "sample", title: "Sample Heritage", region: "Hue" },
    scene_context: { id: 7, key: "s1", slug: "s1", title: "Main Gate", description: null, sequence: 0 },
    conversation_context: [{ role: "user" as const, content: "Tell me about this place." }],
  };

  await requestSceneChat("https://api.example/api", request, {
    fetchImpl: (async (...args: unknown[]) => {
      calls.push(args);
      return { ok: true } as Response;
    }) as typeof fetch,
    randomUUID: () => "correlation-id",
  });

  assert.equal(calls[0][0], "https://api.example/api/chat/message");
  const options = calls[0][1] as { method: string; headers: Record<string, string>; body: string };
  assert.equal(options.method, "POST");
  assert.equal(options.headers["X-Correlation-ID"], "correlation-id");
  assert.deepEqual(JSON.parse(options.body), request);
});

test("scene chat only sends a bearer header when an access token exists", async () => {
  const calls: unknown[][] = [];
  const fetchImpl = (async (...args: unknown[]) => {
    calls.push(args);
    return { ok: true } as Response;
  }) as typeof fetch;

  await requestSceneChat("https://api.example/api", { message: "Hello" }, {
    fetchImpl,
    randomUUID: () => "guest-request",
  });
  await requestSceneChat("https://api.example/api", { message: "Hello" }, {
    fetchImpl,
    accessToken: "access-token",
    randomUUID: () => "account-request",
  });

  const firstOptions = calls[0][1] as { headers: Record<string, string> };
  const secondOptions = calls[1][1] as { headers: Record<string, string> };
  assert.equal("Authorization" in firstOptions.headers, false);
  assert.equal(secondOptions.headers.Authorization, "Bearer access-token");
});

test("guest conversation context stays within the API message and character limits", () => {
  const messages = Array.from({ length: 8 }, (_, index) => ({
    role: index % 2 === 0 ? "user" : "assistant",
    content: `${index}: ${"x".repeat(2500)}`,
  }));

  const context = createConversationContext(messages);

  assert.equal(context.length, 3);
  assert.ok(context.every((message) => message.content.length <= 2000));
  assert.ok(context.reduce((sum, message) => sum + message.content.length, 0) <= 6000);
  assert.equal(context.at(-1)?.content.startsWith("7: "), true);
});

test("guest conversation context includes up to the latest six short messages", () => {
  const messages = Array.from({ length: 8 }, (_, index) => ({
    role: index % 2 === 0 ? "user" : "assistant",
    content: `Message ${index}`,
  }));

  const context = createConversationContext(messages);

  assert.deepEqual(context.map((message) => message.content), [
    "Message 2",
    "Message 3",
    "Message 4",
    "Message 5",
    "Message 6",
    "Message 7",
  ]);
});
