import GlobalProvider from "@/layout/GlobalProvider";
import type { Metadata } from "next";
export { generateMetadata } from "./metadata";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <GlobalProvider appearance="light">{children}</GlobalProvider>
      </body>
    </html>
  );
}


