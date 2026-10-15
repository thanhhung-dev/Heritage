/**
 * Hình dạng URL của tour — gom về một chỗ để nút bấm và bộ đọc route không lệch nhau.
 *
 *   /content/{slug}                   → splash, chọn cảnh
 *   /content/{slug}/{sceneKey}        → đang xem cảnh
 *   /content/{slug}/{sceneKey}/int    → chế độ điểm tương tác (Dive Deeper)
 *
 * Đuôi `/int` tách "đang ở 3D mode" ra khỏi state của component. Nhờ vậy chỉ có
 * MỘT nguồn sự thật cho trạng thái đó: nút Back/Forward chạy đúng, chia sẻ link
 * vào thẳng chế độ 3D được, và không phải đồng bộ state với URL bằng tay.
 */
export const INTERACTIVE_SEGMENT = "int";

/** `/content/{slug}/{sceneKey}` */
export function sceneUrl(slug: string, sceneKey: string): string {
  return `/content/${slug}/${sceneKey}`;
}

/** `/content/{slug}/{sceneKey}/int` */
export function interactiveUrl(slug: string, sceneKey: string): string {
  return `${sceneUrl(slug, sceneKey)}/${INTERACTIVE_SEGMENT}`;
}

/**
 * `pathname` có phải route điểm tương tác không.
 *
 * Đối chiếu CẢ cấu trúc path chứ không chỉ so khớp đuôi: nếu một cảnh có
 * `sceneKey` đúng bằng "int" thì URL `/content/{slug}/int` chỉ có 3 đoạn và
 * KHÔNG được nhận nhầm thành route điểm tương tác.
 */
export function isInteractivePath(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  const parts = pathname.split("/").filter(Boolean);
  return (
    parts.length === 4 &&
    parts[0] === "content" &&
    parts[3] === INTERACTIVE_SEGMENT
  );
}
