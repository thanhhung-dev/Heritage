import type { Metadata } from "next";

const isDev = process.env.NODE_ENV === "development";

export async function generateMetadata(): Promise<Metadata> {
  const APP_NAME = "Heritage";
  const APP_DESCRIPTION =
    "Recruitify is a platform that helps employers find the best candidates for their jobs";

  return {
    title: {
      default: APP_NAME,
      template: `%s · ${APP_NAME}`,
    },

    description: APP_DESCRIPTION,

    metadataBase: new URL(
      isDev ? "http://localhost:3000" : "https://recruitify.com",
    ),

    icons: {
      shortcut: "/favicon.ico",
      apple: "/apple-touch-icon.png",
    },

    alternates: {
      canonical: isDev ? "http://localhost:3000" : "https://recruitify.com",
    },

    openGraph: {
      title: APP_NAME,
      description: APP_DESCRIPTION,
      url: isDev ? "http://localhost:3000" : "https://recruitify.com",
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
