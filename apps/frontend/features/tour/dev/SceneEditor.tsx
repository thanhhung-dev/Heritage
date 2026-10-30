"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { useHeritageTour } from "@/context/heritage-tour";
import { resolveSceneByKey, sceneKeys } from "@/lib/heritage";
import { createSceneDraft, parseSceneDraft, sampleSceneDraft, type EditorPose } from "./scene-draft";
import styles from "./scene-editor.module.css";

const timeLabel = (seconds: number) => `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;

function NumberField({ label, value, min, max, onCommit }: {
  label: string; value: number; min?: number; max?: number; onCommit: (value: number) => void;
}) {
  const [text, setText] = useState(String(Number(value.toFixed(4))));
  useEffect(() => setText(String(Number(value.toFixed(4)))), [value]);
  return <label className={styles.numberField}><span>{label}</span><input
    aria-label={label} type="number" step="any" min={min} max={max} value={text}
    onChange={(event) => setText(event.target.value)}
    onBlur={(event) => {
      const next = Number(text);
      if (text.trim() && Number.isFinite(next) && event.currentTarget.checkValidity()) onCommit(next);
      else setText(String(Number(value.toFixed(4))));
    }}
    onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }}
  /></label>;
}

export default function SceneEditor() {
  const { payload, heritageSlug, currentSceneKey, currentScene, engine, hasModel, modelError, modelProgress, scenePlayback } = useHeritageTour();
  // SceneSurface only mounts the editor for a valid scene.
  const scene = currentScene!;
  const [draft, setDraft] = useState(() => createSceneDraft(heritageSlug, currentSceneKey, scene));
  const [selected, setSelected] = useState<"start" | "end">("start");
  const [saved, setSaved] = useState(JSON.stringify(draft));
  const [storageReady, setStorageReady] = useState(false);
  const [message, setMessage] = useState("");
  const [playing, setPlaying] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [audioError, setAudioError] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const frameRef = useRef(0);
  const previewToken = useRef(0);
  const elapsedRef = useRef(0);
  const draftRef = useRef(draft);
  draftRef.current = draft;
  const storageKey = `heritage:scene-draft:v1:${heritageSlug}:${scene.id}:${currentSceneKey}`;
  const narrationUrl = scenePlayback?.narrationUrl ?? null;
  const duration = narrationUrl ? audioDuration : draft.durationSeconds;
  const dirty = JSON.stringify(draft) !== saved;
  const selectedPose = draft[selected];
  const editable = draft.useAB && !playing;
  const canPreview = !!engine && draft.useAB && !!draft.start && !!draft.end && duration > 0 && !audioError;

  const applyPose = (pose: EditorPose) => engine?.restoreCameraPose({
    position: new THREE.Vector3(...pose.position), target: new THREE.Vector3(...pose.target),
    up: new THREE.Vector3(...pose.up), fov: pose.fov,
  });

  const stop = () => {
    previewToken.current += 1;
    cancelAnimationFrame(frameRef.current);
    audioRef.current?.pause();
    setPlaying(false);
  };

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const restored = parseSceneDraft(raw, heritageSlug, currentSceneKey, scene.id);
        if (restored) {
          setDraft(restored);
          setSaved(JSON.stringify(restored));
          setMessage("Đã mở bản nháp trên máy.");
        } else setMessage("Bản nháp không hợp lệ; đang dùng dữ liệu gốc.");
      }
    } catch { setMessage("Trình duyệt không cho đọc bản nháp. Bạn vẫn có thể xuất JSON."); }
    setStorageReady(true);
  }, [storageKey, heritageSlug, currentSceneKey, scene.id]);

  useEffect(() => {
    if (!engine || !storageReady) return;
    let cancelled = false;
    engine.setPlaybackTime(0, false);
    engine.stopCameraTimeline();
    engine.stopCameraPath();
    engine.releaseHighlightDolly();
    engine.exitExplore();
    engine.setInteractiveHighlights([]);
    engine.setSky(scene.sky);
    void engine.setSceneHighlights([]);
    const initial = engine.getCameraPose();
    // Clear any flight left by the normal viewer before taking editor ownership.
    engine.restoreCameraPose(initial);
    if (scene.camera.path_url && !draftRef.current.useAB) {
      void engine.setCameraPath(scene.camera.path_url).then((ready) => {
        if (!cancelled && ready) engine.applyCameraPathStart(0);
      });
    } else {
      const start = draftRef.current.start;
      if (start) engine.restoreCameraPose({
        position: new THREE.Vector3(...start.position), target: new THREE.Vector3(...start.target),
        up: new THREE.Vector3(...start.up), fov: start.fov,
      });
    }
    const restoreControls = engine.enableCameraEditing();
    const audio = audioRef.current;
    return () => {
      cancelled = true;
      previewToken.current += 1;
      cancelAnimationFrame(frameRef.current);
      audio?.pause();
      restoreControls();
      engine.stopCameraPath();
      engine.stopCameraTimeline();
      engine.setPlaybackTime(0, false);
    };
  }, [engine, storageReady, scene]);

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (dirty) { event.preventDefault(); event.returnValue = ""; }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const confirmLeave = () => !dirty || window.confirm("Bản nháp chưa lưu. Rời editor và bỏ các thay đổi chưa lưu?");

  const capture = (endpoint: "start" | "end") => {
    if (!engine || !editable) return;
    const p = engine.getCameraPose();
    setDraft((previous) => ({ ...previous, [endpoint]: {
      position: p.position.toArray(), target: p.target.toArray(), up: p.up.toArray(), fov: p.fov,
    } }));
    setSelected(endpoint);
    setMessage(`Đã lấy góc ${endpoint === "start" ? "đầu A" : "cuối B"} từ camera hiện tại.`);
  };

  const changePose = (field: "position" | "target", index: number, value: number) => {
    if (!selectedPose) return;
    const next = structuredClone(selectedPose);
    next[field][index] = value;
    if (next.position.every((n, i) => n === next.target[i])) {
      setMessage("Vị trí camera và điểm nhìn không được trùng nhau.");
      return;
    }
    setDraft({ ...draft, [selected]: next });
    applyPose(next);
  };

  const seek = (next: number) => {
    stop();
    elapsedRef.current = next;
    setSeconds(next);
    if (audioRef.current && audioDuration > 0) audioRef.current.currentTime = next;
    const pose = sampleSceneDraft({ ...draft, durationSeconds: duration }, next);
    if (pose) applyPose(pose);
  };

  const preview = async () => {
    if (!canPreview) return;
    if (playing) { stop(); return; }
    const token = ++previewToken.current;
    setPlaying(true);
    const start = elapsedRef.current >= duration ? 0 : elapsedRef.current;
    const audio = audioRef.current;
    if (audio && narrationUrl) {
      audio.currentTime = start;
      try { await audio.play(); }
      catch {
        if (token === previewToken.current) {
          setPlaying(false);
          setMessage("Không phát được audio. Hãy kiểm tra URL hoặc quyền phát âm thanh.");
        }
        return;
      }
    }
    if (token !== previewToken.current) return;
    const startedAt = performance.now();
    const tick = (now: number) => {
      if (token !== previewToken.current) return;
      const next = Math.min(duration, audio && narrationUrl ? audio.currentTime : start + (now - startedAt) / 1000);
      const pose = sampleSceneDraft({ ...draftRef.current, durationSeconds: duration }, next);
      if (pose) applyPose(pose);
      elapsedRef.current = next;
      setSeconds(next);
      if (next >= duration || (audio && narrationUrl && audio.ended)) { stop(); return; }
      frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
  };

  const save = () => {
    const next = { ...draft, durationSeconds: duration > 0 ? duration : draft.durationSeconds };
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
      setDraft(next);
      setSaved(JSON.stringify(next));
      setMessage("Đã lưu bản nháp trên trình duyệt này. Không ghi database.");
    } catch { setMessage("Không lưu được trên máy. Hãy xuất JSON để giữ bản nháp."); }
  };

  const exportDraft = () => {
    const next = { ...draft, durationSeconds: duration > 0 ? duration : draft.durationSeconds };
    const url = URL.createObjectURL(new Blob([JSON.stringify(next, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${heritageSlug}-${currentSceneKey}.scene-draft.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setMessage("Đã xuất JSON bản nháp; đây không phải thao tác xuất bản tour.");
  };

  const reset = () => {
    if (!window.confirm("Khôi phục scene về dữ liệu gốc? Bản nháp đã lưu chỉ bị thay khi bạn bấm Lưu nháp.")) return;
    stop();
    seek(0);
    const original = createSceneDraft(heritageSlug, currentSceneKey, scene);
    setDraft(original);
    setSelected("start");
    if (original.start) applyPose(original.start);
    if (!original.useAB && scene.camera.path_url) {
      void engine?.setCameraPath(scene.camera.path_url).then((ready) => { if (ready) engine?.applyCameraPathStart(0); });
    }
    setMessage("Đã khôi phục dữ liệu gốc trong editor.");
  };

  return <div className={styles.editor}>
    <header className={styles.header}>
      <div className={styles.brand}>H<span>HeritageGraph</span></div>
      <span className={styles.breadcrumb}>{payload.heritage.title}</span>
      <span className={styles.devBadge}>DEV / SCENE EDITOR</span>
      <span className={styles.draftState}>{dirty ? "● Chưa lưu" : "● Bản nháp trên máy"}</span>
      <Link className={styles.exit} href={`/content/${heritageSlug}/${currentSceneKey}`} onClick={(event) => { if (!confirmLeave()) event.preventDefault(); }}>Thoát Dev ↗</Link>
    </header>

    <nav className={styles.scenes} aria-label="Chọn scene để chỉnh sửa">
      <p className={styles.eyebrow}>TOUR WORKSPACE</p><h2>Cảnh trong tour</h2>
      {sceneKeys(payload).map((key, index) => {
        const item = resolveSceneByKey(payload, key);
        return <Link key={key} href={`/content/${heritageSlug}/${key}?dev=scene`}
          className={`${styles.sceneLink} ${key === currentSceneKey ? styles.activeScene : ""}`}
          aria-current={key === currentSceneKey ? "page" : undefined}
          onClick={(event) => { if (key !== currentSceneKey && !confirmLeave()) event.preventDefault(); }}>
          <span className={styles.sceneNumber}>{String(index).padStart(2, "0")}</span><span><small>{key.toUpperCase()}</small>{item?.title ?? key}</span>
        </Link>;
      })}
      <p className={styles.localNote}>Chỉ chỉnh bản nháp.<br />Tour gốc không thay đổi.</p>
    </nav>

    <div className={styles.viewportHint}><span className={styles.liveDot} /> LIVE VIEWPORT <span>Kéo để xoay · Cuộn để zoom · Chuột phải để pan</span></div>
    {!engine && <div className={styles.modelStatus} role="status">{modelError ?? (hasModel ? `Đang chuẩn bị model 3D… ${Math.round(modelProgress * 100)}%` : "Tour chưa có model 3D. Bạn vẫn có thể sửa nội dung và xuất nháp.")}</div>}

    <aside className={styles.inspector} aria-label="Thông số scene">
      <p className={styles.eyebrow}>SCENE {currentSceneKey.toUpperCase()}</p><h1>Dựng góc kể chuyện</h1>
      <label className={styles.field}>Tên scene<input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
      <label className={styles.field}>Mô tả<textarea rows={3} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>

      {scene.camera.path_url && <div className={styles.pathNotice}>
        <strong>{draft.useAB ? "Đang dùng bản nháp A → B" : "Scene đang dùng GLB camera path"}</strong>
        <p>Chuyển sang A → B chỉ ảnh hưởng bản nháp, không xóa path gốc.</p>
        {!draft.useAB && <button type="button" onClick={() => {
          engine?.stopCameraPath();
          if (engine) engine.restoreCameraPose(engine.getCameraPose());
          setDraft({ ...draft, useAB: true });
          setMessage("Đã chuyển bản nháp sang A → B. Hãy lấy hai góc camera.");
        }}>Chuyển sang A → B</button>}
      </div>}

      <div className={styles.sectionHeading}><h2>Camera</h2><span>A → B</span></div>
      <div className={styles.stops} role="group" aria-label="Góc camera đang chỉnh">
        {(["start", "end"] as const).map((endpoint) => <button type="button" key={endpoint}
          className={selected === endpoint ? styles.selectedStop : ""} disabled={!editable}
          aria-pressed={selected === endpoint} onClick={() => {
            stop(); setSelected(endpoint);
            const p = draft[endpoint]; if (p) applyPose(p);
          }}><b>{endpoint === "start" ? "A" : "B"}</b><span>Góc {endpoint === "start" ? "đầu" : "cuối"}<small>{draft[endpoint] ? "Đã có góc" : "Chưa lấy góc"}</small></span></button>)}
      </div>
      <button className={styles.capture} type="button" disabled={!engine || !editable} onClick={() => capture(selected)}>◎ Lấy góc {selected === "start" ? "đầu A" : "cuối B"} từ camera</button>
      <p className={styles.help}>Chọn A hoặc B để xem góc đã lưu. Di chuyển camera rồi bấm lấy góc để cập nhật.</p>

      <fieldset className={styles.coordinates} disabled={!editable || !selectedPose}>
        {(["position", "target"] as const).map((field) => <div key={field}><span className={styles.coordinateLabel}>{field === "position" ? "Vị trí · Position" : "Điểm nhìn · Target"}</span>
          <div className={styles.vector}>{(["X", "Y", "Z"] as const).map((axis, index) => <NumberField key={`${selected}-${field}-${axis}`} label={`${field === "position" ? "Position" : "Target"} ${axis}`} value={selectedPose?.[field][index] ?? 0} onCommit={(value) => changePose(field, index, value)} />)}</div>
        </div>)}
        <NumberField label="FOV (độ)" value={selectedPose?.fov ?? 50} min={10} max={120} onCommit={(fov) => {
          if (!selectedPose) return;
          const next = { ...selectedPose, fov };
          setDraft({ ...draft, [selected]: next }); applyPose(next);
        }} />
      </fieldset>

      <div className={styles.sectionHeading}><h2>Thời lượng</h2><span>{narrationUrl ? "THEO AUDIO" : "TÙY CHỈNH"}</span></div>
      {narrationUrl ? <p className={styles.audioStatus}>{audioError ? "Không tải được audio. Kiểm tra nguồn thuyết minh." : audioDuration > 0 ? `♫ ${timeLabel(audioDuration)} · Đồng bộ thuyết minh` : "Đang đọc thời lượng audio…"}</p>
        : <NumberField label="Thời lượng preview (giây)" value={draft.durationSeconds} min={0.1} onCommit={(value) => { stop(); setDraft({ ...draft, durationSeconds: value }); seek(0); }} />}
      {narrationUrl && <audio ref={audioRef} src={narrationUrl} preload="metadata" onLoadedMetadata={(event) => {
        const value = event.currentTarget.duration;
        if (Number.isFinite(value) && value > 0) { setAudioDuration(value); setAudioError(false); }
      }} onError={() => { stop(); setAudioError(true); }} />}

      <div className={styles.saveActions}><button type="button" className={styles.primary} disabled={!storageReady} onClick={save}>Lưu nháp</button><button type="button" onClick={exportDraft}>Xuất JSON ↗</button></div>
      <p className={styles.safety}>◈ Chỉ lưu trên máy · Không ghi database</p>
      <p className={styles.feedback} role="status" aria-live="polite">{message}</p>
    </aside>

    <section className={styles.timeline} aria-label="Preview chuyển động camera">
      <div className={styles.timelineHeading}><div><span className={styles.eyebrow}>CAMERA PREVIEW</span><h2>{draft.title || "Scene chưa đặt tên"}</h2></div><span className={styles.time}>{timeLabel(seconds)} <span>/ {timeLabel(duration)}</span></span></div>
      <div className={styles.transport}>
        <button type="button" className={styles.play} disabled={!canPreview} onClick={() => void preview()} aria-label={playing ? "Tạm dừng preview" : "Phát preview"}>{playing ? "Ⅱ" : "▶"}</button>
        <div className={styles.track}><div className={styles.trackLabels}><span>A <small>Góc đầu</small></span><span><small>Góc cuối</small> B</span></div>
          <input type="range" min={0} max={duration || 12} step="any" value={Math.min(seconds, duration || 12)} disabled={!canPreview} aria-label="Thời điểm preview" onChange={(event) => seek(Number(event.target.value))} />
        </div>
        <button type="button" disabled={!canPreview} onClick={() => seek(0)}>Về đầu</button><button type="button" onClick={reset}>Khôi phục</button>
      </div>
      <p className={styles.timelineNote}>{!draft.useAB ? "Chuyển sang A → B để dựng đường chạy mới." : !draft.start || !draft.end ? "Lấy đủ hai góc A và B để xem thử chuyển động." : "Preview nội suy A → B. Tạm dừng để tiếp tục chỉnh góc; kéo thanh để tua."}</p>
    </section>
  </div>;
}
