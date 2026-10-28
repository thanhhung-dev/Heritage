"use client";

import { useSyncExternalStore } from "react";
import { useHeritageTour } from "@/context/heritage-tour";
import { ChatOverlayWidget } from "@/features/chat/components/ChatOverlayWidget";
import { useChatOverlay } from "@/features/chat/useChatOverlay";
import { AUTH_CHANGE_EVENT, getAccessToken } from "@/lib/auth";

function subscribe(onChange: () => void) {
  window.addEventListener(AUTH_CHANGE_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(AUTH_CHANGE_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

const serverSession = () => null;

export function HeritageChatOverlay() {
  const { heritageSlug } = useHeritageTour();
  const accessToken = useSyncExternalStore(subscribe, getAccessToken, serverSession);
  // A session/heritage change must never display the previous account's messages.
  return <OverlaySession key={`${heritageSlug}:${accessToken ?? "guest"}`} accessToken={accessToken} />;
}

function OverlaySession({ accessToken }: { accessToken: string | null }) {
  const { payload, currentScene, currentSceneKey, heritageSlug } = useHeritageTour();
  const heritage = payload.heritage;
  const chat = useChatOverlay(accessToken, {
    // The viewer fixture is not a published heritage row in the local database.
    heritage_id: heritageSlug !== "tapestry-test" && heritage.publish_state === "published" ? heritage.id : undefined,
    heritage_context: { title: heritage.title.slice(0, 300), region: heritage.region?.slice(0, 300) ?? null },
    scene_context: {
      key: currentSceneKey, title: currentScene?.title.slice(0, 300) ?? currentSceneKey,
      description: currentScene?.description?.slice(0, 900) ?? null,
    },
  });

  return <ChatOverlayWidget messages={chat.messages} input={chat.input} sending={chat.sending}
    heritageName={heritage.title} authenticated={Boolean(accessToken)}
    error={chat.error} contextLabel={currentScene?.title ?? heritage.title}
    onInputChange={chat.setInput} onSend={(text) => void chat.send(text)} onNewConversation={chat.newConversation} />;
}
