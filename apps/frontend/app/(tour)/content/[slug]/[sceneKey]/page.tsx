"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";

import { useHeritageTour } from "@/context/heritage-tour";
import HeritageViewer from "@/features/tour/HeritageViewer";

/**
 * `/content/{slug}/[sceneKey]` — single scene route (`s0` = overview,
 * `s1..sN` = regular scenes). Data comes from the shared tour context
 * (fetched once in the layout). The 3D canvas is mounted by the 3D team
 * inside `HeritageViewer`'s `#render_area`.
 */
export default function SceneRoute() {
  const params = useParams<{ slug: string; sceneKey: string }>();
  const { setCurrentSceneKey } = useHeritageTour();

  // Keep the shared store in sync with the URL so deeper components
  // (3D loader, nav) read the right `currentScene`.
  useEffect(() => {
    setCurrentSceneKey(params.sceneKey);
  }, [params.sceneKey, setCurrentSceneKey]);

  return <HeritageViewer />;
}