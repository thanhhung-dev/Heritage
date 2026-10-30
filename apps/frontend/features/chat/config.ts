export const CHAT_SUGGESTIONS = [
  "Lăng Tự Đức được xây dựng năm nào?",
  "Cao lầu là món gì?",
  "Festival Huế tổ chức mấy năm một lần?",
  "Làng Non Nước nổi tiếng về gì?",
  "Nhã nhạc cung đình Huế có gì đặc biệt?",
] as const;

export const CHAT_API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const OVERLAY_QUICK_SUGGESTIONS = [
  { label: "Giới thiệu tổng quan", value: "Giới thiệu tổng quan về {heritage}." },
  { label: "Lịch sử hình thành", value: "Lịch sử hình thành của {heritage} là gì?" },
  { label: "Kiến trúc đặc sắc", value: "Kiến trúc của {heritage} có gì đặc sắc?" },
  { label: "Khám phá cảnh này", value: "Giới thiệu về {scene} tại {heritage}." },
] as const;
