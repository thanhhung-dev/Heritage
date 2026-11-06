import assert from "node:assert/strict";
import test from "node:test";

import { buildSceneChatSuggestions } from "../lib/scene-chat-suggestions.mjs";
import { resolveTourArea, tourQuestions } from "../lib/tour-chat-scope.mjs";

const area = resolveTourArea("lang-tu-duc");

test("s0 and the stele story show different questions anchored to their own titles and heritage", () => {
  const overview = buildSceneChatSuggestions(area, { title: "Mở đầu chuyến tham quan", description: null }, "s0");
  const stele = buildSceneChatSuggestions(area, {
    title: "Bia đá và những nỗi niềm", description: "Tìm hiểu những suy tư và giá trị lịch sử của văn bia.",
  }, "s3");
  assert.notDeepEqual(overview.suggestions, stele.suggestions);
  assert.equal(stele.contextLabel, "s3 · Bia đá và những nỗi niềm");
  assert.ok(stele.suggestions.some((item) => item.label === "Ý nghĩa văn bia"));
  for (const item of stele.suggestions) {
    assert.ok(item.value.includes("Bia đá và những nỗi niềm"));
    assert.ok(item.value.includes(area.title));
    assert.equal(item.value.includes("Mở đầu chuyến tham quan"), false);
  }
});

test("suggestions follow the story metadata when scene indices or content change", () => {
  const story = { title: "Khu vườn và cảnh quan", description: "Cảnh quan và hồ nước." };
  const first = buildSceneChatSuggestions(area, story, "s1");
  const reordered = buildSceneChatSuggestions(area, story, "s4");
  assert.deepEqual(first.suggestions, reordered.suggestions);
  assert.ok(first.suggestions.some((item) => item.label === "Cảnh quan nơi này"));
  const edited = buildSceneChatSuggestions(area, { ...story, title: "Cổng và kiến trúc", description: "Chi tiết kiến trúc cổng." }, "s1");
  assert.notDeepEqual(first.suggestions, edited.suggestions);
  assert.ok(edited.suggestions.some((item) => item.label === "Chi tiết kiến trúc"));
});

test("absent story or unsupported area never invents a topic", () => {
  const missing = buildSceneChatSuggestions(area, null, "s9");
  assert.equal(missing.contextLabel, null);
  assert.deepEqual(missing.suggestions.map((item) => item.value), tourQuestions(area));
  assert.deepEqual(buildSceneChatSuggestions(null, { title: "Unregistered tour" }, "s0").suggestions, []);
  const untitled = buildSceneChatSuggestions(area, { title: "  ", description: null }, "s2");
  assert.ok(untitled.suggestions.every((item) => item.value.includes("Câu chuyện s2")));
});

test("metadata is rendered as bounded plain text and suggestions stay short", () => {
  const result = buildSceneChatSuggestions(area, {
    title: `<b>Bia đá</b>\n${"rất dài ".repeat(100)}`,
    description: "<p>Văn bia</p> https://example.test",
  }, "s3");
  assert.equal(result.suggestions.length, 4);
  assert.ok(result.suggestions.every((item) => item.value.length <= 200));
  assert.ok(result.suggestions.every((item) => !/[<>\n]/.test(item.value)));
  assert.equal(result.contextLabel.includes("<b>"), false);
});
