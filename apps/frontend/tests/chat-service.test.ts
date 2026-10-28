import assert from "node:assert/strict";
import test from "node:test";
import {
  ChatApiError, chatErrorMessage, citationSources, getConversationMessages,
  listConversations, sendChatMessage,
} from "../services/chatService";

const citation = {
  id: "citation-1", message_id: "assistant-1", source_title: "Chùa Thiên Mụ",
  source_url: "https://example.org/thien-mu", relevance_score: 0.9,
};
const answer = {
  conversation_id: "conversation-1", message_id: "assistant-1", answer: "Năm 1601.", citations: [citation],
};
const conversation = {
  id: "conversation-1", account_id: 1, title: "Chùa Thiên Mụ", heritage_id: null,
  created_at: "2026-10-26T00:00:00Z", updated_at: "2026-10-26T00:00:00Z",
};
const storedMessage = {
  id: "assistant-1", conversation_id: conversation.id, role: "assistant", content: answer.answer,
  created_at: conversation.created_at, citations: [citation],
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { "Content-Type": "application/json" },
});

test("chat accepts both 201 Created and 200 OK and maps normalized citations", async (t) => {
  let status = 201;
  t.mock.method(globalThis, "fetch", async () => json(answer, status));
  assert.deepEqual(await sendChatMessage({ message: "Câu hỏi" }, null), answer);
  status = 200;
  const result = await sendChatMessage({ message: "Câu hỏi" }, null);
  assert.deepEqual(citationSources(result.citations), [{
    doc: citation.source_title, url: citation.source_url, chunk_id: citation.id,
  }]);
});

test("signed-in chat retains the conversation and bearer token; guests send neither credentials nor an existing id", async (t) => {
  const requests: RequestInit[] = [];
  t.mock.method(globalThis, "fetch", async (url: string, init: RequestInit) => {
    assert.match(url, /\/api\/chat\/message$/);
    assert.doesNotMatch(url, /\/api\/api\//);
    requests.push(init);
    return json(answer, 201);
  });
  const request = { message: "Câu hỏi", conversation_id: conversation.id };
  await sendChatMessage(request, "token-a");
  await sendChatMessage(request, null);
  assert.equal(new Headers(requests[0].headers).get("Authorization"), "Bearer token-a");
  assert.equal(JSON.parse(String(requests[0].body)).conversation_id, conversation.id);
  assert.equal(new Headers(requests[1].headers).has("Authorization"), false);
  assert.equal(JSON.parse(String(requests[1].body)).conversation_id, null);
});

test("sidebar requests the paginated authenticated conversation list", async (t) => {
  const controller = new AbortController();
  const fetchMock = t.mock.method(globalThis, "fetch", async (url: string, init: RequestInit) => {
    assert.match(url, /\/api\/chat\/conversations\?limit=50&offset=50$/);
    assert.equal(new Headers(init.headers).get("Authorization"), "Bearer token-a");
    assert.equal(init.signal, controller.signal);
    assert.equal(init.cache, "no-store");
    return json([conversation]);
  });
  assert.deepEqual(await listConversations("token-a", 50, controller.signal), [conversation]);
  await assert.rejects(listConversations(""), (error: unknown) => error instanceof ChatApiError && error.status === 401);
  assert.equal(fetchMock.mock.callCount(), 1);
});

test("history restores ordered messages and their citations", async (t) => {
  t.mock.method(globalThis, "fetch", async (url: string, init: RequestInit) => {
    assert.match(url, /\/conversations\/conversation-1\/messages\?limit=500&offset=0$/);
    assert.equal(new Headers(init.headers).get("Authorization"), "Bearer token-a");
    return json({ ...conversation, messages: [
      { ...storedMessage, id: "user-1", role: "user", content: "Câu hỏi", citations: [] }, storedMessage,
    ] });
  });
  const messages = await getConversationMessages(conversation.id, "token-a");
  assert.deepEqual(messages.map((message) => message.role), ["user", "assistant"]);
  assert.equal(messages[1].content, answer.answer);
  assert.equal(messages[1].sources?.[0].doc, citation.source_title);
});

test("long conversations load every page without truncating the latest turn", async (t) => {
  const offsets: string[] = [];
  t.mock.method(globalThis, "fetch", async (url: string) => {
    const offset = new URL(url, "http://localhost").searchParams.get("offset")!;
    offsets.push(offset);
    const count = offset === "0" ? 500 : 1;
    return json({ ...conversation, messages: Array.from({ length: count }, (_, index) => ({
      ...storedMessage, id: `message-${Number(offset) + index}`,
    })) });
  });
  const messages = await getConversationMessages(conversation.id, "token-a");
  assert.equal(messages.length, 501);
  assert.deepEqual(offsets, ["0", "500"]);
  assert.equal(messages[500].id, "message-500");
});

test("API errors retain Vietnamese detail and an expired token is never retried as a guest", async (t) => {
  let status = 504;
  const fetchMock = t.mock.method(globalThis, "fetch", async () => json({ detail: "AI xử lý quá thời gian." }, status));
  await assert.rejects(sendChatMessage({ message: "Câu hỏi" }, "expired"), (error: unknown) => {
    assert.ok(error instanceof ChatApiError);
    assert.equal(error.status, 504);
    assert.equal(chatErrorMessage(error), "AI xử lý quá thời gian.");
    return true;
  });
  status = 401;
  await assert.rejects(sendChatMessage({ message: "Câu hỏi" }, "expired"), (error: unknown) => {
    assert.ok(error instanceof ChatApiError);
    assert.equal(error.status, 401);
    assert.match(error.message, /đăng nhập lại/);
    return true;
  });
  assert.equal(fetchMock.mock.callCount(), 2);
});

test("malformed success responses are rejected and unsafe citation URLs are not rendered as links", async (t) => {
  t.mock.method(globalThis, "fetch", async () => json({ answer: "legacy", sources: [] }));
  await assert.rejects(sendChatMessage({ message: "Câu hỏi" }, null), ChatApiError);
  assert.equal(citationSources([{ ...citation, source_url: "javascript:alert(1)" }])[0].url, undefined);
  assert.equal(citationSources([{ ...citation, source_url: null }])[0].doc, citation.source_title);
});
