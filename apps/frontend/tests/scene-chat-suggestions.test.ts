import assert from "node:assert/strict";
import test from "node:test";

import { buildSceneChatSuggestions } from "../lib/scene-chat-suggestions";
import { resolveTourArea } from "../lib/tour-chat-scope";
import { requestSceneChat } from "../lib/scene-chat-request";

const area = resolveTourArea("lang-tu-duc");
const REFERENCE_LABELS = [
  "Giới thiệu tổng quan",
  "Lịch sử hình thành",
  "Kiến trúc đặc sắc",
  "Khám phá cảnh này",
];

test("reviewed branches follow the selected point, hide completed stories and do not invent a replacement", () => {
  assert.ok(area);
  const scene = {
    title: "Cảnh thử nghiệm", guide_stories: [
      { id: "scene-story", label: "Câu chuyện của cảnh", question: "Câu hỏi của cảnh", source_ids: ["fixture-1"] },
    ],
  };
  const point = {
    popup_title: "Điểm được chọn", guide_stories: [
      { id: "point-story", label: "Câu chuyện của điểm", question: "Câu hỏi của điểm", source_ids: ["fixture-2"] },
      { id: "point-detail", label: "Chi tiết khác", question: "Câu hỏi chi tiết", source_ids: ["fixture-3"] },
    ],
  };
  const result = buildSceneChatSuggestions(area, scene, "s3", point, ["point-story"]);
  assert.deepEqual(result.suggestions.map((item) => item.value), ["Câu hỏi chi tiết"]);
  assert.match(result.contextLabel ?? "", /Điểm được chọn/);
  const exhausted = buildSceneChatSuggestions(area, scene, "s3", point, ["point-story", "point-detail"]);
  assert.deepEqual(exhausted.suggestions, []);
  const fallback = buildSceneChatSuggestions(area, { title: "Cảnh khác" }, "s4", { popup_title: "Chi tiết B" });
  assert.ok(fallback.suggestions.every((item) => item.value.includes("Chi tiết B")));
});

test("s0 and the stele story show different questions anchored to their own titles and heritage", () => {
  assert.ok(area);
  const overview = buildSceneChatSuggestions(
    area,
    { title: "Mở đầu chuyến tham quan", description: null },
    "s0",
  );
  const stele = buildSceneChatSuggestions(
    area,
    {
      title: "Bia đá và những nỗi niềm",
      description: "Tìm hiểu những suy tư và giá trị lịch sử của văn bia.",
    },
    "s3",
  );
  assert.notDeepEqual(overview.suggestions, stele.suggestions);
  assert.equal(stele.contextLabel, "s3 · Bia đá và những nỗi niềm");
  assert.deepEqual(stele.suggestions.map((item) => item.label), REFERENCE_LABELS);
  assert.deepEqual(overview.suggestions.map((item) => item.label), REFERENCE_LABELS);
  for (const item of stele.suggestions) {
    assert.ok(item.value.includes("Bia đá và những nỗi niềm"));
    assert.ok(item.value.includes(area.title));
    assert.equal(item.value.includes("Mở đầu chuyến tham quan"), false);
  }
});

test("suggestions follow the story metadata when scene indices or content change", () => {
  assert.ok(area);
  const story = { title: "Khu vườn và cảnh quan", description: "Cảnh quan và hồ nước." };
  const first = buildSceneChatSuggestions(area, story, "s1");
  const reordered = buildSceneChatSuggestions(area, story, "s4");
  assert.deepEqual(first.suggestions, reordered.suggestions);
  assert.ok(first.suggestions.every((item) => item.value.includes(story.title)));
  const edited = buildSceneChatSuggestions(
    area,
    { ...story, title: "Cổng và kiến trúc", description: "Chi tiết kiến trúc cổng." },
    "s1",
  );
  assert.notDeepEqual(first.suggestions, edited.suggestions);
  assert.ok(edited.suggestions.every((item) => item.value.includes("Cổng và kiến trúc")));
});

test("absent story or unsupported area never invents a topic", () => {
  assert.ok(area);
  const missing = buildSceneChatSuggestions(area, null, "s9");
  assert.equal(missing.contextLabel, null);
  assert.deepEqual(missing.suggestions.map((item) => item.label), REFERENCE_LABELS);
  assert.ok(
    missing.suggestions.every((item) => item.value.includes(area.title) && !item.value.includes("s9")),
  );
  assert.deepEqual(
    buildSceneChatSuggestions(null, { title: "Unregistered tour" }, "s0").suggestions,
    [],
  );
  const untitled = buildSceneChatSuggestions(area, { title: "  ", description: null }, "s2");
  assert.ok(untitled.suggestions.every((item) => item.value.includes("Câu chuyện s2")));
});

test("metadata is rendered as bounded plain text and suggestions stay short", () => {
  assert.ok(area);
  const result = buildSceneChatSuggestions(
    area,
    {
      title: `<b>Bia đá</b>\n${"rất dài ".repeat(100)}`,
      description: "<p>Văn bia</p> https://example.test",
    },
    "s3",
  );
  assert.equal(result.suggestions.length, 4);
  assert.ok(result.suggestions.every((item) => item.value.length <= 200));
  assert.ok(result.suggestions.every((item) => !/[<>\n]/.test(item.value)));
  assert.ok(result.contextLabel && !result.contextLabel.includes("<b>"));
  assert.ok(result.suggestions.every((item) => item.label.length <= 32));
});

test("story metadata for a different destination falls back to the locked heritage", () => {
  assert.ok(area);
  for (const story of [
    { title: "Lăng Minh Mạng", description: "" },
    { title: "Câu chuyện", description: "Tham quan Đại Nội." },
    { title: "Hành trình", description: "Khám phá Chùa Linh Mụ" },
  ]) {
    const result = buildSceneChatSuggestions(area, story, "s2");
    assert.equal(result.contextLabel, null);
    assert.deepEqual(result.suggestions.map((item) => item.label), REFERENCE_LABELS);
    assert.ok(result.suggestions.every((item) => item.value.includes(area.title)));
    assert.equal(result.suggestions.some((item) => item.value.includes(story.title)), false);
  }
  const regionalContext = buildSceneChatSuggestions(
    area,
    {
      title: "Khiêm Lăng trong quần thể di tích Cố đô Huế",
      description: null,
    },
    "s0",
  );
  assert.ok(regionalContext.contextLabel?.includes("Khiêm Lăng"));
});

test("every selected story chip serializes its own scene and preserves the active area", async () => {
  assert.ok(area);
  const stories = [
    { id: 10, slug: "s0", title: "Mở đầu chuyến tham quan", description: null },
    { id: 20, slug: "s1", title: "Cổng và kiến trúc", description: "Chi tiết kiến trúc." },
    { id: 30, slug: "s2", title: "Khu vườn và cảnh quan", description: "Hồ nước và cảnh quan." },
    { id: 40, slug: "s3", title: "Bia đá và những nỗi niềm", description: "Giá trị lịch sử của văn bia." },
    { id: 50, slug: "s4", title: "Gìn giữ di sản", description: "Bảo tồn di sản." },
  ];
  const bodies: Array<{
    active_area_id: string;
    scene_context: { key: string; id: number; title: string };
    message: string;
  }> = [];
  for (const story of stories) {
    const presentation = buildSceneChatSuggestions(area, story, story.slug);
    assert.equal(presentation.suggestions.length, 4);
    assert.ok(presentation.contextLabel?.startsWith(story.slug));
    for (const suggestion of presentation.suggestions) {
      await requestSceneChat(
        "https://api.example/api",
        {
          message: suggestion.value,
          active_area_id: area.id,
          heritage_context: { slug: "lang-tu-duc" },
          scene_context: { ...story, key: story.slug },
        },
        {
          fetchImpl: (async (url: string | URL | Request, init?: RequestInit) => {
            assert.equal(url, "https://api.example/api/chat/message");
            bodies.push(JSON.parse(init?.body as string));
            return { ok: true } as Response;
          }) as typeof fetch,
          randomUUID: () => `story-${story.slug}`,
        },
      );
      const sent = bodies.at(-1);
      assert.ok(sent);
      assert.equal(sent.active_area_id, "khiem-lang");
      assert.equal(sent.scene_context.key, story.slug);
      assert.equal(sent.scene_context.id, story.id);
      assert.equal(sent.scene_context.title, story.title);
      assert.ok(sent.message.includes(story.title));
      assert.ok(sent.message.includes(area.title));
    }
  }
  assert.equal(bodies.length, 20);
});
