import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ChatMarkdown } from "../features/chat/components/ChatMarkdown";
import { safeSourceUrl } from "../lib/safe-source-url";
import {
  ChatApiError, chatErrorMessage, citationSources, getConversationMessages,
  listConversations, sendChatMessage,
} from "../services/chatService";
import { guestConversationContext, overlaySuggestions } from "../features/chat/overlay-context";
import type { ChatOverlayMessage } from "../features/chat/types/chatOverlay";
import { getHeritageConversation, sendHeritageChatMessage } from "../services/heritageChatService";
import {
  chatAccountId, chatStorageKey, forgetChat, rememberConversation, rememberedConversation,
  rememberGuestMessages, rememberedGuestMessages, type ChatStorage,
} from "../features/chat/overlay-storage";

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

test("overlay replies retain clarification, abstention and development answer metadata", async (t) => {
  const clarification = {
    ...answer, citations: [], needs_user_choice: true, abstained: false,
    suggestions: [{ suggested: "Cung An Định", original: "cung an", score: 0.9 }],
    answer_type: "suggestion", resolution_status: "ambiguous", abstention_reason: null,
  };
  let payload: unknown = clarification;
  t.mock.method(globalThis, "fetch", async () => json(payload, 201));
  assert.deepEqual(await sendChatMessage({ message: "Which palace?" }, null), clarification);
  payload = {
    ...answer, citations: [], abstained: true, abstention_reason: "insufficient_evidence",
    needs_user_choice: false, answer_type: "insufficient_evidence",
  };
  const result = await sendChatMessage({ message: "Unknown heritage" }, null);
  assert.equal(result.abstained, true);
  assert.equal(result.abstention_reason, "insufficient_evidence");
  payload = { ...answer, answer_type: "development_mock" };
  assert.equal((await sendChatMessage({ message: "Preview" }, null)).answer_type, "development_mock");
});

test("guest context excludes the UI greeting and bounds complete turns", () => {
  const message = (id: string, role: "user" | "assistant", content: string): ChatOverlayMessage => ({
    id, role, content, citations: [], createdAt: "2026-10-29T00:00:00Z",
  });
  const shortHistory = [message("mila-welcome", "assistant", "UI_GREETING"), message("u1", "user", "Question"), message("a1", "assistant", "Answer")];
  assert.deepEqual(guestConversationContext(shortHistory), [
    { role: "user", content: "Question" }, { role: "assistant", content: "Answer" },
  ]);
  const longHistory = Array.from({ length: 12 }, (_, index) => message(
    String(index), index % 2 === 0 ? "user" : "assistant", String(index).repeat(4000),
  ));
  const bounded = guestConversationContext(longHistory);
  assert.ok(bounded.length <= 6);
  assert.equal(bounded[0].role, "user");
  assert.ok(bounded.every((item) => item.content.length <= 2000));
  assert.ok(bounded.reduce((total, item) => total + item.content.length, 0) <= 6000);
  assert.deepEqual(guestConversationContext([message("a", "assistant", "No user question")]), []);
});

test("clarification options preserve usable labels without duplicate or empty choices", () => {
  assert.deepEqual(overlaySuggestions([
    { suggested: " Palace " }, { label: "Temple" }, { suggested: "Palace" }, {}, { suggested: "  " },
  ]), [
    { label: "Palace", value: "Palace" }, { label: "Temple", value: "Temple" },
  ]);
});

test("overlay Markdown renders semantic headings, emphasis and lists", () => {
  const html = renderToStaticMarkup(createElement(ChatMarkdown, {
    content: "## Heritage\n\n**Important** facts:\n\n- First detail\n- Second detail\n\n1. Visit\n2. Explore\n\n`stone`",
  }));
  assert.match(html, /<h3>Heritage<\/h3>/);
  assert.match(html, /<strong>Important<\/strong>/);
  assert.match(html, /<ul>.*First detail.*Second detail.*<\/ul>/s);
  assert.match(html, /<ol.*Visit.*Explore.*<\/ol>/s);
  assert.match(html, /<code>stone<\/code>/);
});

test("overlay Markdown never executes raw HTML or unsafe links", () => {
  const html = renderToStaticMarkup(createElement(ChatMarkdown, {
    content: '<script>alert(1)</script>\n\n[unsafe](javascript:alert(1))\n\n[verified](https://example.org/source)\n\n![remote](https://example.org/tracker.png)',
  }));
  assert.doesNotMatch(html, /<script|<img|href="javascript:/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /href="https:\/\/example.org\/source"/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.equal(safeSourceUrl("https://user:password@example.org/private"), null);
  assert.equal(safeSourceUrl("data:text/html,unsafe"), null);
  assert.equal(safeSourceUrl(null), null);
});

test("heritage service sends heritage/scene and optional auth with the correct Guest policy", async (t) => {
  const requests: RequestInit[] = [];
  t.mock.method(globalThis, "fetch", async (_url: string, init: RequestInit) => { requests.push(init); return json(answer, 201); });
  const history: ChatOverlayMessage[] = [{
    id: "user-1", role: "user", content: "Where is this?", createdAt: conversation.created_at, citations: [],
  }];
  const context = { heritage_id: 10, heritage_context: "Heritage title", scene_context: "Gate" };
  await sendHeritageChatMessage("Follow up", conversation.id, context, history, "token-a");
  await sendHeritageChatMessage("Follow up", conversation.id, context, history, null);
  const account = JSON.parse(String(requests[0].body));
  assert.equal(account.heritage_id, 10);
  assert.equal(account.scene_context, "Gate");
  assert.equal(account.conversation_id, conversation.id);
  assert.equal("conversation_context" in account, false);
  assert.equal(new Headers(requests[0].headers).get("Authorization"), "Bearer token-a");
  const guest = JSON.parse(String(requests[1].body));
  assert.equal(guest.conversation_id, null);
  assert.deepEqual(guest.conversation_context, [{ role: "user", content: "Where is this?" }]);
  assert.equal(new Headers(requests[1].headers).has("Authorization"), false);
});

test("heritage history restores outcomes and rejects account or heritage mismatches", async (t) => {
  t.mock.method(globalThis, "fetch", async () => json({ ...conversation, heritage_id: 10, messages: [{
    ...storedMessage, needs_user_choice: true, suggestions: [{ suggested: "The temple" }],
    abstained: false, answer_type: "suggestion",
  }] }));
  const restored = await getHeritageConversation(conversation.id, "1", 10, "token-a");
  assert.equal(restored[0].createdAt, storedMessage.created_at);
  assert.deepEqual(restored[0].citations, [citation]);
  assert.equal(restored[0].needsUserChoice, true);
  assert.deepEqual(restored[0].suggestions, [{ label: "The temple", value: "The temple" }]);
  await assert.rejects(getHeritageConversation(conversation.id, "2", 10, "token-a"), (error: unknown) => error instanceof ChatApiError && error.status === 403);
  await assert.rejects(getHeritageConversation(conversation.id, "1", 20, "token-a"), (error: unknown) => error instanceof ChatApiError && error.status === 403);
});

class MemoryChatStorage implements ChatStorage {
  private readonly values = new Map<string, string>();
  getItem(key: string) { return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
  removeItem(key: string) { this.values.delete(key); }
}

test("conversation cache scopes account/heritage IDs without storing access tokens or messages", () => {
  const storage = new MemoryChatStorage();
  const token = "header." + Buffer.from(JSON.stringify({ sub: "1" })).toString("base64url") + ".signature";
  assert.equal(chatAccountId(token), "1");
  assert.equal(chatAccountId(null), null);
  assert.equal(chatAccountId("broken-token"), null);
  const key = chatStorageKey("heritage-a", chatAccountId(token));
  const id = "11111111-1111-4111-8111-111111111111";
  rememberConversation(storage, key, id);
  assert.equal(rememberedConversation(storage, key), id);
  assert.equal(rememberedConversation(storage, chatStorageKey("heritage-b", "1")), null);
  assert.equal(rememberedConversation(storage, chatStorageKey("heritage-a", "2")), null);
  assert.equal(storage.getItem(key), id);
  assert.ok(!key.includes(token));
  forgetChat(storage, key);
  assert.equal(rememberedConversation(storage, key), null);
});

test("Guest cache restores bounded turns and rejects corrupt or untrusted stored history", () => {
  const storage = new MemoryChatStorage();
  const key = chatStorageKey("heritage-a", null);
  const messages: ChatOverlayMessage[] = [
    { id: "u", role: "user", content: "Question", createdAt: conversation.created_at, citations: [] },
    { id: "a", role: "assistant", content: "Answer", createdAt: conversation.created_at, citations: [citation], abstained: false },
  ];
  rememberGuestMessages(storage, key, messages);
  assert.deepEqual(rememberedGuestMessages(storage, key), messages);
  assert.equal(JSON.parse(storage.getItem(key)!).conversation_id, undefined);
  storage.setItem(key, JSON.stringify([{ ...messages[0], role: "system" }]));
  assert.deepEqual(rememberedGuestMessages(storage, key), []);
  storage.setItem(key, "invalid JSON");
  assert.deepEqual(rememberedGuestMessages(storage, key), []);
  const long: ChatOverlayMessage[] = Array.from({ length: 20 }, (_, index) => ({
    ...messages[index % 2], id: String(index), content: "x".repeat(8000),
  }));
  rememberGuestMessages(storage, key, long);
  const bounded = rememberedGuestMessages(storage, key);
  assert.ok(bounded.length <= 12);
  assert.ok(bounded.reduce((size, item) => size + item.content.length, 0) <= 24000);
});

test("unavailable browser storage does not prevent an in-memory conversation", () => {
  const blocked: ChatStorage = {
    getItem() { throw new Error("storage disabled"); }, setItem() { throw new Error("quota"); }, removeItem() { throw new Error("storage disabled"); },
  };
  assert.equal(rememberedConversation(blocked, "key"), null);
  assert.deepEqual(rememberedGuestMessages(blocked, "key"), []);
  assert.doesNotThrow(() => rememberConversation(blocked, "key", "11111111-1111-4111-8111-111111111111"));
  assert.doesNotThrow(() => forgetChat(blocked, "key"));
});
