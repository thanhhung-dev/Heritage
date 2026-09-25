export type PublicRouteKey =
  | "home"
  | "explore"
  | "map"
  | "chat"
  | "preferences";

export interface PublicRoute {
  key: PublicRouteKey;
  href: string;
  label: string;
  title: string;
  description: string;
}

export const PUBLIC_ROUTES = [
  {
    key: "home",
    href: "/",
    label: "Trang chủ",
    title: "Di sản sống trong từng câu chuyện",
    description:
      "Không gian khám phá di sản văn hóa Đà Nẵng - Huế đang được hoàn thiện.",
  },
  {
    key: "explore",
    href: "/explore",
    label: "Khám phá",
    title: "Khám phá di sản",
    description:
      "Nội dung tuyển chọn, chủ đề và bộ sưu tập di sản sẽ xuất hiện tại đây.",
  },
  {
    key: "map",
    href: "/map",
    label: "Bản đồ",
    title: "Bản đồ di sản",
    description:
      "Trải nghiệm khám phá di sản theo địa điểm đang được xây dựng.",
  },
  {
    key: "chat",
    href: "/chat",
    label: "Hỏi đáp",
    title: "Trợ lý di sản",
    description: "Đặt câu hỏi và khám phá tri thức di sản theo cách tự nhiên.",
  },
  {
    key: "preferences",
    href: "/preferences",
    label: "Sở thích",
    title: "Sở thích khám phá",
    description:
      "Tùy chọn cá nhân hóa nội dung và hành trình khám phá đang được hoàn thiện.",
  },
] as const satisfies readonly PublicRoute[];

export const PUBLIC_NAVIGATION_ITEMS = [
  { key: "home", href: "/", label: "Home" },
  { key: "map", href: "/map", label: "Map" },
  { key: "explore", href: "/explore", label: "Library" },
  { key: "chat", href: "/chat", label: "FAQ" },
] as const;

export const PUBLIC_ROUTE_BY_KEY = Object.fromEntries(
  PUBLIC_ROUTES.map((route) => [route.key, route]),
) as Record<PublicRouteKey, PublicRoute>;
