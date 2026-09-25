import type { Metadata } from "next";
import "@fontsource/poppins/400.css";
import "@fontsource/poppins/600.css";
import "./globals.css";
export { generateMetadata } from "./metadata";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}


