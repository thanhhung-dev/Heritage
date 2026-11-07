import assert from "node:assert/strict";
import test from "node:test";
import { resolveTourArea, tourQuestions, validateTourReply } from "../lib/tour-chat-scope";
import { requestSceneChat } from "../lib/scene-chat-request";

test("tour identity resolves explicit aliases and never guesses unsupported titles", () => {
  for (const slug of ["khiem-lang", "lang-tu-duc", "tu-duc-tomb"]) {
    assert.equal(resolveTourArea(slug)?.id, "khiem-lang");
  }
  assert.equal(resolveTourArea("tapestry-test"), null);
  assert.equal(resolveTourArea("random-khiem-lang-tour"), null);
  const area = resolveTourArea("lang-tu-duc");
  assert.ok(area && tourQuestions(area).every((question) => question.includes(area.title)));
});

test("replies require matching area, source provenance and bounded followups", () => {
  const reply = {
    active_area_id: "khiem-lang",
    answer_type: "answered",
    answer: "Verified answer",
    sources: [{ passage_id: "42", active_area_id: "khiem-lang" }],
    follow_up_questions: ["Kiến trúc của Khiêm Lăng có gì đặc sắc?"],
  };
  assert.deepEqual(validateTourReply(reply, "khiem-lang"), reply.follow_up_questions);
  for (const change of [
    { active_area_id: undefined },
    { active_area_id: "lang-minh-mang" },
    { sources: [{ passage_id: "legacy" }] },
    { sources: [] },
    { sources: [{ passage_id: "foreign", active_area_id: "lang-minh-mang" }] },
    { follow_up_questions: [null] },
    { follow_up_questions: Array(4).fill("Question") },
    { answer_type: "conversation" },
  ]) {
    assert.throws(() => validateTourReply({ ...reply, ...change }, "khiem-lang"));
  }
  assert.deepEqual(
    validateTourReply({ ...reply, sources: [], answer_type: "out_of_scope" }, "khiem-lang"),
    reply.follow_up_questions,
  );
});

test("changing area aborts the old request; the next payload carries only its own area/history", async () => {
  const pending = new AbortController();
  const calls: Record<string, unknown>[] = [];
  const fetchImpl = (async (_url: string | URL | Request, init?: RequestInit) => {
    if (init?.body && typeof init.body === "string") {
      calls.push(JSON.parse(init.body));
    }
    if (init?.signal) {
      return new Promise<Response>((_, reject) => {
        init.signal?.addEventListener(
          "abort",
          () => reject(new DOMException("Aborted", "AbortError")),
          { once: true },
        );
      });
    }
    return { ok: true } as Response;
  }) as typeof fetch;

  const oldRequest = requestSceneChat(
    "/api",
    {
      message: "Vua Tự Đức sống ở đây thế nào?",
      active_area_id: "khiem-lang",
      conversation_context: [{ role: "user", content: "Khiêm Lăng" }],
    },
    { signal: pending.signal, fetchImpl, randomUUID: () => "old" },
  );
  pending.abort();
  await assert.rejects(oldRequest, { name: "AbortError" });
  await requestSceneChat(
    "/api",
    {
      message: "Giới thiệu khu vực này",
      active_area_id: "lang-minh-mang",
      conversation_context: [],
    },
    { fetchImpl, randomUUID: () => "new" },
  );
  assert.equal(calls[1].active_area_id, "lang-minh-mang");
  assert.deepEqual(calls[1].conversation_context, []);
});
