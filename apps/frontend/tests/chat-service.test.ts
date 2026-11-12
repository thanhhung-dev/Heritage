import assert from "node:assert/strict";
import test, { type TestContext } from "node:test";
import { ChatApiError, sendChatMessage, getConversationHistory, listConversations, deleteConversation } from "../services/chatService";

const conversationId = "11111111-1111-4111-8111-111111111111";
const messageId = "22222222-2222-4222-8222-222222222222";
const reply = {
  conversation_id: conversationId, message_id: messageId,
  answer: "Câu trả lời có nguồn", answer_type: "answered", active_area_id: "khiem-lang",
  sources: [{ passage_id: "42", doc: "Nguồn Khiêm Lăng", url: "https://example.test/source", active_area_id: "khiem-lang" }],
  follow_up_questions: [], needs_user_choice: false, abstained: false,
};

test("tour replies require the request snapshot and restored messages retain their original scene", async (t) => {
  browser(t);
  const context = { scene_id: 506, mode: "standard" as const, highlight_id: 6, narration: "partial" as const };
  const snapshot = { scene_id: 506, scene_key: "s3", scene_title: "Cảnh gốc", mode: "standard", highlight_id: 6,
    highlight_title: "Điểm gốc", story_id: null };
  globalThis.fetch = async () => new Response(JSON.stringify({ ...reply, reply_context: snapshot }));
  const result = await sendChatMessage({ message: "Kể thêm", active_area_id: "khiem-lang", tour_context: context });
  assert.deepEqual(result.replyContext, snapshot);
  globalThis.fetch = async () => new Response(JSON.stringify({ ...reply, reply_context: { ...snapshot, scene_id: 508 } }));
  await assert.rejects(sendChatMessage({ message: "Kể thêm", active_area_id: "khiem-lang", tour_context: context }), /ngữ cảnh/);
  globalThis.fetch = async () => new Response(JSON.stringify(reply));
  await assert.rejects(sendChatMessage({ message: "Kể thêm", active_area_id: "khiem-lang", tour_context: context }), /ngữ cảnh/);
  globalThis.fetch = async () => new Response(JSON.stringify({ id: conversationId, active_area_id: "khiem-lang", total_messages: 1,
    messages: [{ ...reply, id: messageId, role: "assistant", content: reply.answer, reply_context: snapshot }],
  }));
  const history = await getConversationHistory(conversationId);
  assert.deepEqual(history.messages[0].replyContext, snapshot);
});

function browser(t: TestContext) {
  const values = new Map<string, string>([["heritage_access_token", "test-access-token"]]);
  const originalWindow = Object.getOwnPropertyDescriptor(globalThis, "window");
  const originalStorage = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  const originalFetch = globalThis.fetch;
  Object.defineProperty(globalThis, "window", { configurable: true, value: {} });
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: { getItem: (key: string) => values.get(key) ?? null } });
  t.after(() => {
    globalThis.fetch = originalFetch;
    if (originalWindow) Object.defineProperty(globalThis, "window", originalWindow); else Reflect.deleteProperty(globalThis, "window");
    if (originalStorage) Object.defineProperty(globalThis, "localStorage", originalStorage); else Reflect.deleteProperty(globalThis, "localStorage");
  });
  return values;
}

test("transient chat accepts replies without persistence IDs and preserves scoped citations", async (t) => {
  const values = browser(t);
  const requests: RequestInit[] = [];
  globalThis.fetch = async (_url, init) => {
    requests.push(init ?? {});
    return new Response(JSON.stringify({
      answer: reply.answer, answer_type: reply.answer_type, active_area_id: reply.active_area_id,
      sources: reply.sources, follow_up_questions: [], needs_user_choice: false, abstained: false,
    }));
  };
  const result = await sendChatMessage({ message: "Câu hỏi", active_area_id: "khiem-lang" });
  assert.equal(result.answer, reply.answer);
  assert.equal("conversationId" in result, false);
  assert.match(result.messageId, /^[0-9a-f-]{36}$/i);
  assert.equal(result.sources[0].doc, "Nguồn Khiêm Lăng");
  assert.equal((requests[0].headers as Record<string, string>).Authorization, "Bearer test-access-token");
  values.delete("heritage_access_token");
  await sendChatMessage({ message: "Guest" });
  assert.equal("Authorization" in (requests[1].headers as Record<string, string>), false);
});

test("expired authentication, wrong scope and malformed replies fail safely", async (t) => {
  browser(t);
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: "expired" }), { status: 401 });
  await assert.rejects(sendChatMessage({ message: "test" }), (error: unknown) => error instanceof ChatApiError && error.status === 401);
  globalThis.fetch = async () => new Response(JSON.stringify({ ...reply, active_area_id: "lang-minh-mang" }));
  await assert.rejects(sendChatMessage({ message: "test", active_area_id: "khiem-lang" }), /đúng khu vực/);
  globalThis.fetch = async () => new Response(JSON.stringify({ answer: "old server" }));
  await assert.rejects(sendChatMessage({ message: "test" }), /không đúng định dạng/);
});

test("list, restore and delete use account-owned API data without losing outcome fields", async (t) => {
  browser(t);
  const urls: string[] = [];
  globalThis.fetch = async (url, init) => {
    urls.push(String(url));
    if (init?.method === "DELETE") return new Response(null, { status: 204 });
    if (String(url).includes("/messages")) return new Response(JSON.stringify({
      id: conversationId, active_area_id: "khiem-lang", total_messages: 1,
      messages: [{ id: messageId, conversation_id: conversationId, role: "assistant", content: "Bạn muốn hỏi gì?",
        sources: [], answer_type: "clarification", needs_user_choice: true, abstained: false }],
    }));
    return new Response(JSON.stringify([{ id: conversationId, title: "Hội thoại" }]));
  };
  assert.equal((await listConversations())[0].id, conversationId);
  const history = await getConversationHistory(conversationId);
  assert.equal(history.messages[0].answerType, "clarification");
  assert.equal(history.messages[0].needsUserChoice, true);
  await deleteConversation(conversationId);
  assert.ok(urls[0].includes("/chat/conversations?limit=100"));
  assert.ok(urls[1].includes(`/${conversationId}/messages`));
});
