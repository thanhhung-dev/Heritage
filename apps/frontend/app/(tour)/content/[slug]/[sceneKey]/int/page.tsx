/**
 * Route chế độ điểm tương tác: `/content/{slug}/{sceneKey}/int`.
 *
 * Không render gì — toàn bộ giao diện 3D đã do layout của `content/[slug]` dựng
 * sẵn và nó đọc chính URL này để biết đang ở chế độ nào. Route chỉ tồn tại để
 * trạng thái "đang Dive Deeper" trở thành một URL thật.
 *
 * Xem `lib/tour-routes.ts` để biết vì sao đuôi `/int` tồn tại.
 */
export default function InteractiveRoute() {
  return null;
}
