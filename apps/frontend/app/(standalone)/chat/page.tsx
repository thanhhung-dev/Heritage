import type { Metadata } from "next";
import { ChatExperience } from "@/features/chat/ChatExperience";
import { PUBLIC_ROUTE_BY_KEY } from "@/config/public-navigation";

const route = PUBLIC_ROUTE_BY_KEY.chat;

export const metadata: Metadata = {
  title: route.title,
  description: route.description,
  alternates: { canonical: route.href },
};

export default function ChatPage() {
  return <ChatExperience />;
}
