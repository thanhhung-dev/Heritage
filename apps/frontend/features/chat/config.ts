export const CHAT_SUGGESTIONS = [
  "Lăng Tự Đức được xây dựng năm nào?",
  "Cao lầu là món gì?",
  "Festival Huế tổ chức mấy năm một lần?",
  "Làng Non Nước nổi tiếng về gì?",
  "Nhã nhạc cung đình Huế có gì đặc biệt?",
] as const;

export const CHAT_API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
