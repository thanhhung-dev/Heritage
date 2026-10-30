"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useHeritageTour } from "@/context/heritage-tour";
import HeritageViewer from "./HeritageViewer";
import styles from "./dev/scene-editor.module.css";

const SceneEditor = process.env.NODE_ENV === "development"
  ? dynamic(() => import("./dev/SceneEditor"), { ssr: false }) : null;

export default function SceneSurface({ interactiveRoute, editingScene }: { interactiveRoute: boolean; editingScene: boolean }) {
  const { heritageSlug, currentSceneKey, currentScene } = useHeritageTour();
  const base = `/content/${heritageSlug}/${currentSceneKey}`;
  if (SceneEditor && editingScene && currentScene) {
    return <SceneEditor key={`${heritageSlug}/${currentScene.id}`} />;
  }
  return <>
    <HeritageViewer interactiveRoute={interactiveRoute} />
    {SceneEditor && <Link className={styles.launcher} href={`${base}?dev=scene`}>DEV · Scene Editor ↗</Link>}
  </>;
}
