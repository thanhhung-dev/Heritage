"use client";

import {
  FileTextOutlined,
  FullscreenExitOutlined,
  FullscreenOutlined,
  LeftOutlined,
  MenuOutlined,
  MutedOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
  RightOutlined,
  SettingOutlined,
  ShareAltOutlined,
  SoundOutlined,
  StepForwardOutlined,
} from "@ant-design/icons";
import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type RefObject } from "react";
import logoText from "@/access/icons/logo-text.svg";
import { useHeritageTour } from "@/context/heritage-tour";
import { resolveSceneByKey, sceneKeys } from "@/lib/heritage";
import { tapestryTourVarsStyle } from "@/styles/theme/tapestryTheme";
import Fullscreen from "@/access/icons/full_screen.png";
import FullScreenExit from "@/access/icons/full_screen_exit.png"
import Captions from "@/access/icons/trans_icon.png"
import sound_off from "@/access/icons/sound_off.png"
import sound_on from "@/access/icons/sound_on.png"
import Pause from "@/access/icons/pause.svg"
import Play from "@/access/icons/play.svg"
import { useTourPlayer } from "./player/useTourPlayer";
import ExploreControls from "./components/ExploreControls";
import HighlightPanel from "./components/HighlightPanel";
import Replay from "@/access/icons/replay.svg"
import skip_voicer from "@/access/icons/skip_voicer.svg"
import styles from "./styles.module.css";
import next_scene from "@/access/icons/next_scene.svg"
export default function HeritageViewer() {
  const { slug, sceneKey } = useParams<{ slug: string; sceneKey: string }>();
  const router = useRouter();
  const { payload, currentScene } = useHeritageTour();

  // Trang thử dùng narration/VTT từ tour.json; payload backend chưa có các URL này.
  const player = useTourPlayer();
  const { isPlaying, isMuted, setIsMuted, ccOn, setCcOn } = player;
  const progress = player.duration > 0 ? player.currentTime / player.duration * 100 : 0;
  const formatTime = (seconds: number) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
  const elapsed = formatTime(player.currentTime);
  const total = formatTime(player.duration);

  // UI state
  const [menuOpen, setMenuOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Carousel refs
  const intViewportRef = useRef<HTMLDivElement>(null);

  // Scene navigation
  const keys = sceneKeys(payload);
  const scene = currentScene;
  const index = keys.indexOf(sceneKey);

  // Vòng đời phát của scene hiện tại.
  // "idle"  → vừa vào scene, chưa phát gì: hiện Replay + Skip Voiceover.
  // "ended" → narration chạy hết (hoặc scene không có audio): hiện Prev + Next.
  // Lưu kèm `key` = playbackKey để trạng thái cũ của scene trước KHÔNG thể rò rỉ:
  // khi sang scene mới, `endedFor` khác key ⇒ tự động coi như "idle".
  const playbackKey = `${slug}/${sceneKey}`;
  const [endedScene, setEndedScene] = useState<string | null>(null);
  // Scene này đã từng báo "chưa kết thúc" chưa — chặn cờ ended cũ lọt vào lúc mới vào.
  const sceneSawNotEnded = useRef(false);
  const lastPlaybackKey = useRef(playbackKey);
  if (lastPlaybackKey.current !== playbackKey) {
    lastPlaybackKey.current = playbackKey;
    sceneSawNotEnded.current = false;
  }

  const hasAudio = player.hasAudio;
  // Chỉ "ended" nếu trạng thái ended thuộc ĐÚNG scene hiện tại.
  const isEnded = endedScene === playbackKey;

  // Vừa vào scene: tạm hiện Prev Scene trong ~2 giây đầu, sau đó mới đổi sang
  // Replay Scene. Cho người dùng thời gian ngắn để quay lại scene trước.
  const ARRIVAL_PREV_MS = 2000;
  const [showArrivalPrev, setShowArrivalPrev] = useState(true);

  useEffect(() => {
    // Vào scene mới: về "idle" ngay (bỏ trạng thái ended của scene trước).
    setEndedScene(null);
    sceneSawNotEnded.current = false;
  }, [playbackKey]);

  useEffect(() => {
    // Chưa có audio (chưa gắn URL narration) thì coi như scene đã kết thúc.
    if (!hasAudio) {
      setEndedScene(playbackKey);
      return;
    }
    // Bỏ qua cờ ended cũ của scene trước cho tới khi scene này tự báo chưa kết thúc.
    if (!player.hasEnded) {
      sceneSawNotEnded.current = true;
      return;
    }
    if (sceneSawNotEnded.current) setEndedScene(playbackKey);
  }, [hasAudio, player.hasEnded, playbackKey]);

  // Đếm ngược 2 giây mỗi khi vào scene mới để tắt Prev tạm thời.
  useEffect(() => {
    setShowArrivalPrev(true);
    const timer = window.setTimeout(() => setShowArrivalPrev(false), ARRIVAL_PREV_MS);
    return () => window.clearTimeout(timer);
  }, [playbackKey]);

  // Tự động phát narration khi vào scene (overview s0 hoặc sau khi bấm Next/Prev).
  // Trình duyệt chỉ cho autoplay sau một thao tác người dùng; ở đây người dùng đã
  // bấm "Bắt đầu trải nghiệm" hoặc nút điều hướng nên thường đã có gesture.
  // Nếu bị chặn, useNarration sẽ ghi lỗi — nuốt lỗi để không hiện cảnh báo.
  const autoplayRef = useRef(player.play);
  autoplayRef.current = player.play;
  useEffect(() => {
    if (!hasAudio) return;
    let cancelled = false;
    const timer = window.setTimeout(() => {
      if (!cancelled) void autoplayRef.current().catch(() => {});
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [hasAudio, playbackKey]);

  // Chuyển cảnh: màn đen mờ dần che lúc camera bay, rồi mở ra (kiểu CyArk Tapestry).
  // Dùng CSS transition của .sceneFade qua thuộc tính opacity điều khiển bằng class.
  const [sceneFading, setSceneFading] = useState(false);
  useEffect(() => {
    setSceneFading(true);
    const timer = window.setTimeout(() => setSceneFading(false), 620);
    return () => window.clearTimeout(timer);
  }, [playbackKey]);

  // Trong ~2s đầu ở scene mới: hiện Prev Scene. Sau đó (hoặc khi narration kết thúc
  // và còn scene trước): hiện theo trạng thái ended.
  const arrivalPrev = showArrivalPrev && index > 0 && !isEnded;
  const showPrev = (isEnded && index > 0) || arrivalPrev;
  const showNextScene = isEnded;

  const goPrev = () => {
    if (index > 0) router.push(`/content/${slug}/${keys[index - 1]}`);
  };
  const goNext = () => {
    if (index >= 0 && index < keys.length - 1) {
      router.push(`/content/${slug}/${keys[index + 1]}`);
    }
  };
  // Replay = tua narration về đầu rồi phát lại, đồng thời đưa thanh điều khiển
  // về lại pha "idle" (hiện Replay + Skip Voiceover + các nút 15s).
  const handleReplay = () => {
    // Chờ scene này báo chưa-kết-thúc trở lại rồi mới nhận tín hiệu ended mới.
    sceneSawNotEnded.current = false;
    setEndedScene(null);
    // Replay xong thì nút phải là Replay, không phải Prev tạm thời.
    setShowArrivalPrev(false);
    if (player.exploreMode) player.exitExplore();
    player.restart();
  };
  // Skip Voiceover = nhảy narration tới cuối scene hiện tại (không chuyển scene).
  // Đưa pha về "ended" để nút đổi thành Next Scene + hiện Prev.
  const handleSkipVoiceover = () => {
    setEndedScene(playbackKey);
    player.skipVoiceover();
  };

  const sceneTitle = (key: string) =>
    resolveSceneByKey(payload, key)?.title ?? key;

  useEffect(() => {
    if (!menuOpen) return;
    const mobile = window.matchMedia("(max-width: 640px)");
    const onResize = () => {
      if (!mobile.matches) setMenuOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        document.getElementById("mobileHamburgerBtn")?.focus();
      }
    };
    mobile.addEventListener("change", onResize);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      mobile.removeEventListener("change", onResize);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  // Fullscreen
  useEffect(() => {
    const onChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const toggleFullscreen = async () => {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen();
    } else {
      await document.exitFullscreen();
    }
  };

  const handleSeek = player.seekBy;

  const scrollCarousel = (ref: RefObject<HTMLDivElement | null>, dir: -1 | 1) => {
    ref.current?.scrollBy({ left: dir * 200, behavior: "smooth" });
  };

  return (
    <div className={styles.viewer} style={tapestryTourVarsStyle}>
      <div className={styles.topNavBar}>
        <button
          id="logo"
          type="button"
          className={styles.topNav_logo}
          aria-label="Tapestry"
        >
          <Image
            className={`${styles.tapestryLogo} ${styles.tapestryLogo_icon}`}
            src="https://pub-2fc54e5237344dc9b845f2ff2c9309f8.r2.dev/icon/Heritages.svg"
            alt="Tapestry logo icon"
            width={29}
            height={29}
            unoptimized
          />
          <Image
            className={`${styles.tapestryLogo} ${styles.tapestryLogo_type}`}
            src={logoText}
            alt="Tapestry"
            width={146}
            height={29}
            unoptimized
          />
        </button>
      </div>

      {/* Stop nav: vertical skewed tiles, left edge */}
      <nav
        id="story-panel"
        className={styles.stopNav}
        role="tablist"
        aria-label="Tour navigation"
      >
        <div className={styles.ssNavBars}>
          {keys.map((key) => {
            const active = key === sceneKey;
            return (
              <div key={key} className={styles.ssNavBarGroup}>
                <Link
                  href={`/content/${slug}/${key}`}
                  role="tab"
                  aria-selected={active}
                  className={`${styles.ssNavBar} ${active ? styles.ssActiveNavBar : ""}`}
                  data-no={key}
                  aria-label={`Scene ${key}`}
                  title={sceneTitle(key)}
                >
                  <span className={styles.ssDivBarText}>{sceneTitle(key)}</span>
                </Link>
              </div>
            );
          })}
        </div>
      </nav>

      {/* Stop header: title and description for the active scene */}
      <div className={`${styles.stopHeader} ${styles.fadeIn}`}>
        <h1 className={styles.stopTitle}>{scene?.title}</h1>
        <div className={styles.stopDivider} />
        <p className={styles.stopDesc}>{scene?.description}</p>
      </div>

      {/* Attribution */}
      <footer className={styles.attributionBar} aria-label="Data attribution">
        <p>{payload.heritage.region}</p>
      </footer>

      {/* Scene-transition blackout */}
      <div className={`${styles.sceneFade} ${sceneFading ? styles.sceneFadeActive : ""}`} aria-hidden="true" />

      {/* Bottom media strip */}
      <div
        id="mediaStrip"
        className={styles.mediaStrip}
        style={{ display: "flex" }}
      >
        {/* Closed captions */}
        <div
          className={styles.closedCaptionsGroup}
          id="closedCaptionsGroup"
          style={{ display: ccOn ? "block" : "none" }}
        >
          <div className={styles.closedCaptions} id="closedCaptions">
            <div
              className={styles.closedCaptionsText}
              dir="auto"
              id="closedCaptionsText"
            >{player.captionText}</div>
          </div>
        </div>

        <div
          className={styles.mediaStripContent}
          id="mediaStripContent"
          style={{ display: "block" }}
        >
          {/* Interactive media carousel */}
          <div className={styles.intMediaCarousel} id="intMediaCarousel">
            <button
              tabIndex={0}
              className={`${styles.carouselArrow} ${styles.navIconBg}`}
              id="intCarouselArrow_left"
              aria-label="Scroll left"
              onClick={() => scrollCarousel(intViewportRef, -1)}
            >
              <LeftOutlined
                className={`${styles.navIcons} ${styles.carouselArrowIcon}`}
                aria-hidden="true"
              />
            </button>

            <div
              className={styles.intCarouselViewport}
              id="intCarouselViewport"
              ref={intViewportRef}
            >
              <div
                className={styles.intMediaCarouselItems}
                id="intMediaCarouselItems"
              />
            </div>

            <button
              tabIndex={0}
              className={`${styles.carouselArrow} ${styles.navIconBg}`}
              id="intCarouselArrow_right"
              aria-label="Scroll right"
              onClick={() => scrollCarousel(intViewportRef, 1)}
            >
              <RightOutlined
                className={`${styles.navIcons} ${styles.carouselArrowIcon}`}
                aria-hidden="true"
              />
            </button>
          </div>

          {/* Playback timeline */}
          <div className={styles.playbackTimeline} id="playbackTimeline">
            <div
              className={styles.playbackTimelineFill}
              id="playbackTimelineFill"
              style={{ width: `${progress}%` }}
            />
            <span
              className={`${styles.playbackTime} ${styles.playbackTimeElapsed}`}
              id="playbackTimeElapsed"
            >
              {elapsed}
            </span>
            <span
              className={`${styles.playbackTime} ${styles.playbackTimeTotal}`}
              id="playbackTimeTotal"
            >
              {total}
            </span>
          </div>

          {/* Strip controls */}
          <div className={styles.stripControls}>
            {/* Info controls */}
            <div className={styles.infoControls} id="infoControls">
              <button
                tabIndex={-1}
                className={`${styles.navIconBg} ${styles.tutIcon}`}
                id="tutBg"
                aria-label="Tutorial"
                aria-disabled="true"
                disabled
                style={{ pointerEvents: "none" }}
              >
                <QuestionCircleOutlined
                  className={styles.navIcons}
                  id="tut"
                  aria-hidden="true"
                />
                <div className={styles.navToolTip}>Tutorial</div>
              </button>

              <button
                tabIndex={0}
                className={styles.navIconBg}
                id="resourcesIcon"
                aria-label="Resources"
              >
                <FileTextOutlined
                  className={styles.navIcons}
                  aria-hidden="true"
                />
                <div className={styles.navToolTip}>Resources</div>
              </button>

              <button
                tabIndex={0}
                className={styles.navIconBg}
                id="shareIcon"
                aria-label="Share this location"
              >
                <ShareAltOutlined
                  className={styles.navIcons}
                  aria-hidden="true"
                />
                <div className={styles.navToolTip}>Share</div>
              </button>

              <button
                tabIndex={0}
                className={styles.navIconBg}
                id="settingsIcon"
                aria-label="Settings Mode"
              >
                <SettingOutlined
                  className={styles.navIcons}
                  aria-hidden="true"
                />
                <div className={styles.navToolTip}>Settings</div>
              </button>
            </div>

            {/* Playback controls */}
            <div className={styles.playbackControls}>
              {/* Previous scene / Replay scene (cùng một nút) */}
              <button
                id="prev-replay"
                className={`${styles.ssPrevButton} ${styles.ssButton} ${styles.ssButtonPC}`}
                aria-label={showPrev ? "Previous scene" : "Replay scene"}
                onClick={showPrev ? goPrev : handleReplay}
              >
                <div className={styles.ssInnerButton}>
                  {showPrev ? (
                    <LeftOutlined aria-hidden="true" className={styles.ssButtonImg} />
                  ) : (
                    <Image className={styles.ssButtonImg} src={Replay} alt="replay" aria-hidden="true" />
                  )}
                  <div className={styles.ssNavToolTip}>
                    {showPrev ? "Previous Scene" : "Replay Scene"}
                  </div>
                </div>
              </button>

              {/* Back 15 — làm mờ & khóa khi narration đã hết */}
              <button
                tabIndex={0}
                id="ssBack15"
                className={`${styles.ssMiddleButton} ${styles.ssSeekButton} ${isEnded ? styles.ssControlDisabled : ""}`}
                aria-label="Skip back 15 seconds"
                aria-disabled={isEnded}
                disabled={isEnded}
                onClick={() => handleSeek(-15)}
              >
                <svg
                  className={styles.ssSeekImg}
                  viewBox="0 0 24 24"
                  width={24}
                  height={24}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth={1.6}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                  <path d="M3 3v5h5" />
                  <text
                    x={12}
                    y={15.5}
                    textAnchor="middle"
                    fontSize={8.5}
                    fontWeight={600}
                    fontFamily="sans-serif"
                    fill="#ffffff"
                    stroke="none"
                  >
                    15
                  </text>
                </svg>
                <div className={styles.ssNavToolTip}>Back 15 seconds</div>
              </button>

              {/* Play / Pause — làm mờ & khóa khi hết video */}
              <div
                id="ssMiddleButtonPress"
                className={`${styles.middleButtonGroup} ${isEnded ? styles.ssControlDisabled : ""}`}
                style={{ display: "flex" }}
                aria-disabled={isEnded}
              >
                <div
                  id="ssAudioButton"
                  className={styles.ssAudioButton}
                  style={{ display: "flex", scale: "1" }}
                >
                  <button
                    id="ssPlayButton"
                    className={`${styles.ssMiddleButton} ${styles.ssPlayButton}`}
                    aria-label="Play"
                    disabled={!player.hasAudio}
                    title={!player.hasAudio ? "Chưa có URL narration" : undefined}
                    onClick={() => void player.play()}
                    style={{ display: isPlaying ? "none" : "block" }}
                  >
                    <Image
                      className={`${styles.ssPlayPauseImg}`}
                      src={Play}
                      alt="play"
                      height={24}
                      width={24}
                    />
                    <div className={styles.ssNavToolTip}>Play</div>
                  </button>

                  <button
                    id="ssPauseButton"
                    className={`${styles.ssMiddleButton} ${styles.ssPauseButton}`}
                    aria-label="Pause"
                    onClick={player.pause}
                    style={{ display: isPlaying ? "block" : "none" }}
                  >
                    <Image
                      className={styles.ssPlayPauseImg}
                      src={Pause}
                      alt="pause"
                      height={24}
                      width={24}
                    />
                    <div className={styles.ssNavToolTip}>Pause</div>
                  </button>
                </div>

                <div id="intButtonRing" />
              </div>

              {/* Forward 15 — làm mờ & khóa khi narration đã hết */}
              <button
                tabIndex={0}
                id="ssForward15"
                className={`${styles.ssMiddleButton} ${styles.ssSeekButton} ${isEnded ? styles.ssControlDisabled : ""}`}
                aria-label="Skip forward 15 seconds"
                aria-disabled={isEnded}
                disabled={isEnded}
                onClick={() => handleSeek(15)}
              >
                <svg
                  className={styles.ssSeekImg}
                  viewBox="0 0 24 24"
                  width={24}
                  height={24}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth={1.6}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
                  <path d="M21 3v5h-5" />
                  <text
                    x={12}
                    y={15.5}
                    textAnchor="middle"
                    fontSize={8.5}
                    fontWeight={600}
                    fontFamily="sans-serif"
                    fill="#ffffff"
                    stroke="none"
                  >
                    15
                  </text>
                </svg>
                <div className={styles.ssNavToolTip}>Forward 15 seconds</div>
              </button>

              {/* Next scene / Skip */}
              <div className={styles.ringButtonGroup}>
                <button
                  tabIndex={0}
                  className={`${styles.ssNextButton} ${styles.ssButton} ${styles.ssButtonPC} ${showNextScene ? styles.ssGlow : ""}`}
                  id="next-0"
                  aria-label={showNextScene ? "Next scene" : "Skip narration"}
                  onClick={showNextScene ? goNext : handleSkipVoiceover}
                  disabled={showNextScene && (index === -1 || index === keys.length - 1)}
                  style={{ filter: "brightness(1)", pointerEvents: "all" }}
                >
                  <div
                    className={styles.ssInnerButton}
                    id="ssN-Next"
                    style={{ display: showNextScene ? "inline-flex" : "none" }}
                  >
                    <Image src={next_scene} alt="next_scene" aria-hidden="true" className={styles.ssButtonImg} />
                    <div className={styles.ssNavToolTip}>Next Scene</div>
                  </div>
                  <div
                    className={styles.ssInnerButton}
                    id="ssN-Skip"
                    style={{ display: showNextScene ? "none" : "inline-flex" }}
                  >
                    <Image className={styles.ssButtonImg} src={skip_voicer} alt="skip_voicer" aria-hidden="true" />
                    <div className={styles.ssNavToolTip}>Skip Voiceover</div>
                  </div>
                </button>
                <div
                  className={`${styles.ssNextButtonRing} ${styles.ping} ${styles.rounded}`}
                  id="ssNextButtonRing"
                  style={{ display: "none" }}
                />
              </div>
            </div>

            {/* System controls */}
            <div className={styles.systemControls} id="systemControls">
              <button
                tabIndex={0}
                className={`${styles.navIconBg} ${styles.mobileHamburgerBtn}`}
                id="mobileHamburgerBtn"
                aria-label="Menu"
                aria-expanded={menuOpen}
                aria-controls="mobileGlassMenu"
                onClick={() => setMenuOpen((v) => !v)}
              >
                <MenuOutlined className={styles.navIcons} aria-hidden="true" />
              </button>

              <button
                tabIndex={0}
                className={styles.navIconBg}
                id="navMute"
                aria-label="Mute sound"
                onClick={() => setIsMuted(true)}
                style={{ display: isMuted ? "none" : "flex" }}
              >
                <Image
                  className={styles.navIcons}
                  src={sound_on}
                  alt="sound_on"
                  height={24}
                  width={24}
                />
                <div className={styles.navToolTip}>Sound Off</div>
              </button>

              <button
                tabIndex={0}
                className={styles.navIconBg}
                id="navUnmute"
                aria-label="Unmute sound"
                onClick={() => setIsMuted(false)}
                style={{ display: isMuted ? "flex" : "none" }}
              >
                <Image
                  className={styles.navIcons}
                  src={sound_off}
                  alt="sound_off"
                  height={24}
                  width={24}
                />
                <div className={styles.navToolTip}>Sound On</div>
              </button>

              <div
                className={styles.additionalIcons}
                style={{ display: "flex" }}
              >
                <button
                  tabIndex={0}
                  className={styles.navIconBg}
                  id="ccIconBg"
                  aria-label="Toggle Closed Captions"
                  aria-pressed={ccOn}
                  onClick={() => setCcOn((v) => !v)}
                >
                  <Image
                    className={`${styles.navIcons} ${styles.captionIcon}`}
                    src={Captions}
                    alt="captions"
                    width={24}
                    style={{ opacity: ccOn ? 1 : 0.5 }}
                    height={24}
                  />
                  <div className={styles.navToolTip}>Closed Captions</div>
                </button>
              </div>

              <button
                tabIndex={0}
                className={styles.navIconBg}
                id="fullScreenIcon"
                aria-label="Fullscreen Mode"
                onClick={toggleFullscreen}
                style={{ display: isFullscreen ? "none" : "flex" }}
              >
                <Image
                  className={styles.navIcons}
                  src={Fullscreen}
                  alt="Fullscreen"
                  width={24}
                  height={24}
                />

                <div className={styles.navToolTip}>Fullscreen Mode</div>
              </button>

              <button
                tabIndex={0}
                className={styles.navIconBg}
                id="exitFullScreenIcon"
                aria-label="Exit fullscreen Mode"
                onClick={toggleFullscreen}
                style={{ display: isFullscreen ? "flex" : "none" }}
              >
                <Image
                  className={styles.navIcons}
                  src={FullScreenExit}
                  alt="FullscreenExit"
                  width={24}
                  height={24}
                />
                <div className={styles.navToolTip}>Exit fullscreen Mode</div>
              </button>
            </div>
          </div>
        </div>
      </div>

      {menuOpen && (
        <>
          <button
            type="button"
            className={styles.mobileGlassBackdrop}
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          />
          <nav id="mobileGlassMenu" className={styles.mobileGlassMenu} aria-label="Mobile controls">
            <Link
              href={`/content/${slug}`}
              className={styles.mobileGlassMenu_logo}
              aria-label="Back to splash page"
              onClick={() => setMenuOpen(false)}
            >
              <Image src={logoText} alt="Heritage" width={146} height={29} unoptimized />
            </Link>
            <ul className={styles.mobileGlassMenu_list}>
              {[
                { id: "tutBg", label: "Tutorial", icon: QuestionCircleOutlined, disabled: true },
                { id: "resourcesIcon", label: "Resources", icon: FileTextOutlined, disabled: true },
                { id: "shareIcon", label: "Share", icon: ShareAltOutlined, disabled: true },
                { id: "settingsIcon", label: "Settings", icon: SettingOutlined, disabled: true },
                { id: isMuted ? "navUnmute" : "navMute", label: isMuted ? "Sound On" : "Sound Off", icon: isMuted ? MutedOutlined : SoundOutlined, onClick: () => setIsMuted((value) => !value), pressed: isMuted },
                { id: "ccIconBg", label: "Closed Captions", icon: null, onClick: () => setCcOn((value) => !value), pressed: ccOn },
                { id: isFullscreen ? "exitFullScreenIcon" : "fullScreenIcon", label: isFullscreen ? "Exit fullscreen Mode" : "Fullscreen Mode", icon: isFullscreen ? FullscreenExitOutlined : FullscreenOutlined, onClick: () => { setMenuOpen(false); void toggleFullscreen(); } },
              ].map(({ id, label, icon: Icon, disabled, onClick, pressed }) => (
                <li key={id}>
                  <button
                    type="button"
                    className={styles.mobileGlassMenu_item}
                    data-btn-id={id}
                    disabled={disabled}
                    aria-pressed={pressed}
                    onClick={onClick}
                  >
                    {Icon ? <Icon className={styles.mobileGlassMenu_icon} aria-hidden="true" /> : <span className={`${styles.mobileGlassMenu_icon} ${styles.captionIcon}`} aria-hidden="true">CC</span>}
                    <span className={styles.mobileGlassMenu_label}>{label}</span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </>
      )}

      {/* Transient toast */}
      <div className={styles.toast} role="status" aria-live="polite" />
      {isEnded && <ExploreControls interactive={player.interactive} mode={player.exploreMode}
        onEnter={player.enterExplore} onReset={player.resetExplore} onExit={player.exitExplore}
        initialMode={player.initialExploreMode} onSelectHighlight={player.selectHighlight}
        selectedHighlightId={player.selectedHighlight?.id} />}
      <HighlightPanel highlight={player.selectedHighlight} onClose={player.closeHighlight} />
      {(player.error || player.captionsError) && <p className={styles.playerError} role="alert">{player.error || player.captionsError}</p>}
    </div>
  );
}
