import type { Metadata } from "next";

export async function generateMetadata(): Promise<Metadata> {
  const APP_NAME = "Heritage";
  const APP_DESCRIPTION =
    "Khám phá và kết nối với di sản văn hóa Đà Nẵng - Huế.";
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

  return {
    title: {
      default: APP_NAME,
      template: `%s · ${APP_NAME}`,
    },

    description: APP_DESCRIPTION,

    metadataBase: new URL(appUrl),

    icons: {
      shortcut: "/favicon.ico",
      apple: "/apple-touch-icon.png",
    },

    alternates: {
      canonical: appUrl,
    },

    openGraph: {
      title: APP_NAME,
      description: APP_DESCRIPTION,
      url: appUrl,
      siteName: APP_NAME,
      images: [
        {
          url: "/og-image.png",
          width: 1200,
          height: 630,
          alt: APP_NAME,
        },
      ],
      type: "website",
    },

    twitter: {
      card: "summary_large_image",
      title: APP_NAME,
      description: APP_DESCRIPTION,
      images: ["/og-image.png"],
    },

    manifest: "/manifest.json",
  };
}
