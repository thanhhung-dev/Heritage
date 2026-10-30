"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Suspense, useEffect, useState } from "react";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";

import { HeritageTourProvider } from "@/context/heritage-tour";
import { LogoText } from "@/components/LogoText";
import SceneSurface from "@/features/tour/SceneSurface";
import HeritageCanvas from "@/features/tour/three/HeritageCanvas";
import type { TourEngine } from "@/features/tour/three/tour-engine";
import { TEST_TOUR } from "@/features/tour/tour-data";
import { ApiError } from "@/config/api";
import { fetchTourContent, sceneKeys, type TourPlayback } from "@/lib/heritage";
import { isInteractivePath } from "@/lib/tour-routes";
import { tapestryTourVarsStyle } from "@/styles/theme/heritageTheme";
import type { HeritagePayload } from "@/types/heritage";
import editorStyles from "@/features/tour/dev/scene-editor.module.css";
import styles from "./content-shell.module.css";

type TourState = {
  /** `null` = payload thật chưa về (đang tải hoặc lỗi). Không còn payload demo. */
  payload: HeritagePayload | null;
  error: string | null;
  /** Audio + timing theo scene, lấy từ `GET /api/heritages/{slug}/tour`. */
  playback?: Record<string, TourPlayback>;
  modelUrl: string | null;
};

const NOT_FOUND_MESSAGE =
  "Không tìm thấy tour cho địa điểm này. Có thể địa điểm chưa được xuất bản.";

/**
 * Fullscreen 3D tour layout (`/content/{slug}/...`).
 *
 * The tour renders from the single-load payload of
 * `GET /api/heritages/{slug}/tour` — scenes, narration and the model URL all come
 * from the database, so the page never shows invented content. While the request
 * is in flight the splash frame is rendered with the Start button's loading bar
 * (no separate "loading" screen); only a real failure shows a message.
 * Navigating between `/s0..sN` never refetches.
 */
export default function HeritageContentLayout({ children }: { children: ReactNode }) {
  return <Suspense fallback={null}><HeritageContentWorkspace>{children}</HeritageContentWorkspace></Suspense>;
}

function HeritageContentWorkspace({ children }: { children: ReactNode }) {
  const params = useParams<{ slug: string; sceneKey?: string }>();
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const editingScene = process.env.NODE_ENV === "development" && search.get("dev") === "scene" && !!params.sceneKey;
  const slug = params.slug;
  // `/content/{slug}/{sceneKey}/int` ⇒ đang ở chế độ điểm tương tác. Layout là nơi
  // biết URL, nên nó quyết định; `HeritageViewer` và `useTourPlayer` chỉ tiêu thụ
  // cờ này, không tự đoán lại từ pathname.
  const interactiveRoute = isInteractivePath(pathname);
  const fixture = slug === "tapestry-test" ? TEST_TOUR : null;
  const [engine, setEngine] = useState<TourEngine | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);
  /** 0..1 — tiến độ tải GLB, đẩy lên trang splash để thanh loading chạy theo % thật. */
  const [modelProgress, setModelProgress] = useState(0);

  const [state, setState] = useState<TourState>({
    payload: fixture?.payload ?? null,
    error: null,
    playback: fixture?.playback,
    modelUrl: fixture?.modelUrl ?? null,
  });

  const payload = fixture?.payload ?? state.payload;

  // Scene lấy từ DB (`GET /api/heritages/{slug}/tour`) nên KHÔNG phụ thuộc model 3D:
  // model có thể chưa có trên R2 mà nội dung scene vẫn phải mở được. Chỉ chặn khi
  // payload thật đã về và sceneKey không tồn tại (deep-link sai).
  const sceneKeyValid =
    !params.sceneKey ||
    !payload ||
    sceneKeys(payload).includes(params.sceneKey);

  useEffect(() => {
    if (params.sceneKey && !sceneKeyValid) {
      router.replace(`/content/${slug}`);
    }
  }, [params.sceneKey, sceneKeyValid, router, slug]);

  useEffect(() => {
    if (fixture) return;
    let cancelled = false;

    fetchTourContent(slug)
      .then((tour) => {
        if (cancelled) return;
        const next = tour?.payload;
        const hasContent = !!next && (!!next.overview || next.scenes.length > 0);
        if (!next || !hasContent) {
          setState({ payload: null, error: NOT_FOUND_MESSAGE, modelUrl: null });
          return;
        }
        setState({
          payload: next,
          error: null,
          playback: tour.playback,
          modelUrl: tour.modelUrl ?? null,
        });
      })
      .catch((err) => {
        if (cancelled) return;
        // 404 = slug không tồn tại/chưa xuất bản: thông báo gọn, không phơi chuỗi
        // lỗi HTTP thô của apiClient.
        const notFound = err instanceof ApiError && err.status === 404;
        setState({
          payload: null,
          error: notFound
            ? NOT_FOUND_MESSAGE
            : err instanceof Error && err.message
              ? `Không tải được tour: ${err.message}`
              : "Không tải được tour từ backend.",
          modelUrl: null,
        });
      });

    return () => {
      cancelled = true;
    };
  }, [slug, fixture]);

  if (!payload) {
    // Lỗi thật (404 / backend chết) mới được phép có màn riêng.
    if (state.error) {
      return (
        <div className={styles.shell}>
          <div className={styles.statusScreen} role="status" aria-live="polite">
            <p className={styles.statusTitle}>Không mở được tour</p>
            <p className={styles.statusHint}>{state.error}</p>
            <Link className={styles.statusLink} href="/">
              Về trang chủ
            </Link>
          </div>
        </div>
      );
    }

    // Chưa có payload: dựng ĐÚNG khung của trang splash (logo góc trên + thanh
    // loading của nút Start ở đúng vị trí cuối trang), không mở một màn "đang
    // tải" riêng nào nữa. Mọi thứ đang tải — payload, bytes GLB, giải mã model —
    // đều chạy trong đúng thanh này. Khi payload về, info card chỉ chèn vào phía
    // trên thanh nên thanh không nhảy chỗ và % đang chạy không bị reset.
    return (
      <main className={styles.loading} style={tapestryTourVarsStyle}>
        <div className={styles.splashWrap}>
          <div className={styles.splash} aria-hidden="true" />
        </div>

        <LogoText className={styles.sHeritageLogo} size={100} />

        <div className={styles.pageGroup}>
          <div className={styles.enterButtonGroup}>
            <span
              className={styles.bottomNav}
              role="status"
              aria-live="polite"
              aria-label="Loading heritage assets"
            >
              <span className={styles.loadingBarMain}>
                <span className={styles.loadingBar} aria-hidden="true" />
                <span
                  className={`${styles.loadingBarFill} ${styles.loadingBarFillLoading}`}
                  aria-hidden="true"
                />
                <span className={styles.loadingBarText}>Loading…</span>
              </span>
            </span>
          </div>
        </div>
      </main>
    );
  }

  return (
    <div className={styles.shell}>
      <HeritageTourProvider
        payload={payload}
        heritageSlug={slug}
        currentSceneKey={params.sceneKey ?? "s0"}
        error={state.error}
        engine={engine}
        modelError={modelError}
        modelProgress={modelProgress}
        hasModel={Boolean(fixture?.modelUrl ?? state.modelUrl)}
        playback={fixture?.playback ?? state.playback}
      >
        <HeritageCanvas
          viewportClassName={editingScene ? editorStyles.canvasViewport : undefined}
          onReady={setEngine}
          onError={setModelError}
          onProgress={(progress) => setModelProgress(progress.ratio)}
          // `null` (không phải `undefined`) để báo rõ "chưa có model": HeritageCanvas
          // chỉ dựng engine khi có URL, còn không thì hiện ảnh splash làm nền.
          modelUrl={fixture?.modelUrl ?? state.modelUrl ?? null}
          fallbackImageUrl={payload.heritage.splash_image_url}
        />
        {params.sceneKey ? <SceneSurface interactiveRoute={interactiveRoute} editingScene={editingScene} /> : null}
        {children}
      </HeritageTourProvider>
    </div>
  );
}
