"use client";

import {
  CaretRightFilled,
  CompassOutlined,
  FileTextOutlined,
  FullscreenExitOutlined,
  FullscreenOutlined,
  LeftOutlined,
  MenuOutlined,
  MutedOutlined,
  PauseOutlined,
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

import { useHeritageTour } from "@/context/heritage-tour";
import { resolveSceneByKey, sceneKeys } from "@/lib/heritage";
import { tapestryTourVarsStyle } from "@/styles/theme/tapestryTheme";
import styles from "./styles.module.css";

export default function HeritageViewer() {
  const { slug, sceneKey } = useParams<{ slug: string; sceneKey: string }>();
  const router = useRouter();
  const { payload, currentScene } = useHeritageTour();

  // Playback / audio state
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [elapsed, setElapsed] = useState("0:00");
  const [total, setTotal] = useState("1:05");

  // UI state
  const [ccOn, setCcOn] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Carousel refs
  const intViewportRef = useRef<HTMLDivElement>(null);

  // Scene navigation
  const keys = sceneKeys(payload);
  const scene = currentScene;
  const index = keys.indexOf(sceneKey);

  const goPrev = () => {
    if (index > 0) router.push(`/content/${slug}/${keys[index - 1]}`);
  };
  const goNext = () => {
    if (index >= 0 && index < keys.length - 1) {
      router.push(`/content/${slug}/${keys[index + 1]}`);
    }
  };

  const sceneTitle = (key: string) =>
    resolveSceneByKey(payload, key)?.title ?? key;

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

  // Media handlers (TODO: nối với audio/video ref)
  const handleRestart = () => {
    // TODO: audio.currentTime = 0
    setIsPlaying(true);
  };

  const handleSeek = (_seconds: number) => {
    // TODO: audio.currentTime += _seconds
  };

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
            src="https://pub-2fc54e5237344dc9b845f2ff2c9309f8.r2.dev/icon/svgviewer-output%20(1).svg"
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
      <div className={styles.sceneFade} aria-hidden="true" />

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
              className={`${styles.closedCaptionsText} ${styles.rightToLeftText}`}
              id="closedCaptionsText"
            />
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
              {/* Previous scene */}
              <button
                tabIndex={0}
                className={`${styles.ssPrevButton} ${styles.ssButton} ${styles.ssButtonPC}`}
                id="prev-o"
                aria-label="Previous scene"
                onClick={goPrev}
                disabled={index <= 0}
              >
                <div className={styles.ssInnerButton} id="ssP-Prev">
                  <LeftOutlined
                    aria-hidden="true"
                    className={styles.ssButtonImg}
                  />
                  <div className={styles.ssNavToolTip} id="ssPrevButtonTooltip">
                    Previous Scene
                  </div>
                </div>
              </button>

              {/* Replay scene */}
              <button
                tabIndex={0}
                className={`${styles.ssButton} ${styles.ssButtonPC}`}
                id="ssP-Restart"
                aria-label="Restart narration"
                onClick={handleRestart}
              >
                <div className={styles.ssInnerButton}>
                  <ReloadOutlined
                    aria-hidden="true"
                    className={styles.ssButtonImg}
                  />
                  <div className={styles.ssNavToolTip} id="ssRestartTooltip">
                    Replay Scene
                  </div>
                </div>
              </button>

              {/* Back 15 */}
              <button
                tabIndex={0}
                id="ssBack15"
                className={`${styles.ssMiddleButton} ${styles.ssSeekButton}`}
                aria-label="Skip back 15 seconds"
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

              {/* Play / Pause / Explore */}
              <div
                id="ssMiddleButtonPress"
                className={styles.middleButtonGroup}
                style={{ display: "flex" }}
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
                    onClick={() => setIsPlaying(true)}
                    style={{ display: isPlaying ? "none" : "block" }}
                  >
                    <CaretRightFilled
                      id="ssPlayButton_img"
                      aria-hidden="true"
                      className={styles.ssPlayPauseImg}
                    />
                    <div className={styles.ssNavToolTip}>Play</div>
                  </button>

                  <button
                    id="ssPauseButton"
                    className={`${styles.ssMiddleButton} ${styles.ssPauseButton}`}
                    aria-label="Pause"
                    onClick={() => setIsPlaying(false)}
                    style={{ display: isPlaying ? "block" : "none" }}
                  >
                    <PauseOutlined
                      id="ssPauseButton_img"
                      aria-hidden="true"
                      className={styles.ssPlayPauseImg}
                    />
                    <div className={styles.ssNavToolTip}>Pause</div>
                  </button>
                </div>

                <button
                  id="ssExploreButton"
                  className={styles.ssExploreButton}
                  style={{ display: "none", width: 50 }}
                  aria-label="Explore in 3D"
                >
                  <CompassOutlined
                    id="ssExploreButton_img"
                    aria-hidden="true"
                    className={`${styles.ssExploreImg} ${styles.ssPlaypenStill}`}
                  />
                  <div className={styles.ssExploreFootsteps} aria-hidden="true">
                    <svg
                      className={`${styles.footstep} ${styles.footstepL}`}
                      width={14}
                      height={32}
                      viewBox="0 0 14 32"
                      fill="#FEF0D7"
                    >
                      <path d="M3.26487 26.2322C3.65327 28.7649 5.99176 30.5248 8.53295 30.1969C11.1641 29.8574 12.9984 27.4162 12.5922 24.7945L12.196 22.2365C12 20.9716 10.8158 20.1051 9.55089 20.3011L4.83844 21.0311C3.55869 21.2294 2.68126 22.4266 2.87757 23.7066L3.26487 26.2322Z" />
                      <path d="M5.04955 0.557214C-0.557487 2.09686 0.311432 11.627 1.72526 17.471C1.95668 18.4275 2.88435 19.0279 3.86028 18.901L9.79358 18.1292C10.5353 18.0327 11.1684 17.5354 11.3447 16.8085C12.72 11.1371 12.2236 -1.41273 5.04955 0.557214Z" />
                    </svg>
                    <svg
                      className={`${styles.footstep} ${styles.footstepR}`}
                      width={14}
                      height={32}
                      viewBox="0 0 14 32"
                      fill="#FEF0D7"
                    >
                      <path d="M10.0672 26.2361C9.67876 28.7688 7.34027 30.5287 4.79908 30.2008C2.1679 29.8613 0.333633 27.4201 0.739791 24.7984L1.13608 22.2404C1.33203 20.9755 2.51627 20.109 3.78114 20.305L8.49359 21.035C9.77334 21.2333 10.6508 22.4305 10.4545 23.7105L10.0672 26.2361Z" />
                      <path d="M8.27857 0.557214C13.8856 2.09686 13.0167 11.627 11.6029 17.471C11.3714 18.4275 10.4438 19.0279 9.46785 18.901L3.53455 18.1292C2.79285 18.0327 2.15972 17.5354 1.98346 16.8085C0.608173 11.1371 1.10449 -1.41273 8.27857 0.557214Z" />
                    </svg>
                  </div>
                  <span
                    id="ssExploreButton_text"
                    className={styles.ssExploreButtonText}
                    style={{ display: "none" }}
                  >
                    Explore
                  </span>
                  <div className={styles.ssNavToolTip}>Explore in 3D</div>
                </button>

                <div id="intButtonRing" />
              </div>

              {/* Forward 15 */}
              <button
                tabIndex={0}
                id="ssForward15"
                className={`${styles.ssMiddleButton} ${styles.ssSeekButton}`}
                aria-label="Skip forward 15 seconds"
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
                  className={`${styles.ssNextButton} ${styles.ssButton} ${styles.ssButtonPC}`}
                  id="next-0"
                  aria-label="Skip narration"
                  onClick={goNext}
                  disabled={index === -1 || index === keys.length - 1}
                  style={{ filter: "brightness(1)", pointerEvents: "all" }}
                >
                  <div
                    className={styles.ssInnerButton}
                    id="ssN-Next"
                    style={{ display: "none" }}
                  >
                    <RightOutlined
                      aria-hidden="true"
                      className={styles.ssButtonImg}
                    />
                    <div className={styles.ssNavToolTip}>Next Scene</div>
                  </div>
                  <div
                    className={styles.ssInnerButton}
                    id="ssN-Skip"
                    style={{ display: "inline-flex" }}
                  >
                    <StepForwardOutlined
                      aria-hidden="true"
                      className={styles.ssButtonImg}
                    />
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
                <SoundOutlined className={styles.navIcons} aria-hidden="true" />
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
                <MutedOutlined className={styles.navIcons} aria-hidden="true" />
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
                  <span
                    className={`${styles.navIcons} ${styles.captionIcon}`}
                    id="ccIcon"
                    style={{ opacity: ccOn ? 1 : 0.5 }}
                    aria-hidden="true"
                  >
                    CC
                  </span>
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
                <FullscreenOutlined
                  className={styles.navIcons}
                  aria-hidden="true"
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
                <FullscreenExitOutlined
                  className={styles.navIcons}
                  aria-hidden="true"
                />
                <div className={styles.navToolTip}>Exit fullscreen Mode</div>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Transient toast */}
      <div className={styles.toast} role="status" aria-live="polite" />

      {/* Highlight details */}
      <aside
        className={styles.hotspotPopup}
        hidden
        aria-label="Highlight details"
      >
        <button
          className={styles.hotspotPopupClose}
          type="button"
          aria-label="Close highlight"
        >
          &times;
        </button>
        <div className={styles.hotspotPopupMedia} />
        <h2 id="hotspot-popup-title" />
        <p id="hotspot-popup-text" />
      </aside>

      {/* Caption display */}
      <div className={styles.captionDisplay} aria-live="polite" />
    </div>
  );
}
