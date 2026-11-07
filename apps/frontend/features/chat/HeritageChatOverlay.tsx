"use client";

import { useSyncExternalStore } from "react";
import { useHeritageTour } from "@/context/heritage-tour";
import { ChatOverlayWidget } from "@/features/chat/components/ChatOverlayWidget";
import { useTapestryChat } from "@/features/chat/useTapestryChat";
import { AUTH_CHANGE_EVENT, getAccessToken } from "@/lib/auth";

function subscribe(onChange: () => void) {
  window.addEventListener(AUTH_CHANGE_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => { window.removeEventListener(AUTH_CHANGE_EVENT, onChange); window.removeEventListener("storage", onChange); };
}
function readSession() { try { return getAccessToken(); } catch { return null; } }
const serverSession = () => null;

export function HeritageChatOverlay() {
  const { heritageSlug } = useHeritageTour();
  const accessToken = useSyncExternalStore(subscribe, readSession, serverSession);
  return <OverlaySession key={`${heritageSlug}:${accessToken ?? "guest"}`} accessToken={accessToken} />;
}

function OverlaySession({ accessToken }: { accessToken: string | null }) {
  const { payload, currentScene } = useHeritageTour();
  const chat = useTapestryChat(accessToken);
  const heritage = payload.heritage.title.slice(0, 300);
  const scene = currentScene?.title.slice(0, 300) ?? heritage;
  return <ChatOverlayWidget messages={chat.messages} input={chat.input} sending={chat.sending} error={chat.error}
    onInputChange={chat.setInput} onNewConversation={chat.newConversation}
    onSend={(text) => void chat.send(text?.replaceAll("{heritage}", heritage).replaceAll("{scene}", scene))} />;
}
