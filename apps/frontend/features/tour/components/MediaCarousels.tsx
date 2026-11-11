"use client";

import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { useEffect, useRef, type RefObject } from "react";
import type {
  HeritageInteractiveHighlight,
  HeritageMediaItem,
  HeritageVoice,
  HeritageVoiceClip,
} from "@/types/heritage";
import styles from "../styles.module.css";

const NAV_ITEMS_CDN = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/nav_items";
const UI_ICONS_CDN = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/icons";

export type ActiveTourPopup =
  | { kind: "overview_voice"; voice: HeritageVoice }
  | { kind: "scene_voice"; clip: HeritageVoiceClip }
  | { kind: "media_item"; item: HeritageMediaItem }
  | null;

function scrollByOffset(ref: RefObject<HTMLDivElement | null>, dir: -1 | 1) {
  ref.current?.scrollBy({ left: dir * 220, behavior: "smooth" });
}

export function SceneMediaCarousel({
  visible,
  isOverview,
  voices,
  voiceClips,
  mediaItems,
  visitedVoices,
  onSelectOverviewVoice,
  onSelectSceneVoiceClip,
  onSelectMediaItem,
}: {
  visible: boolean;
  isOverview: boolean;
  voices: HeritageVoice[];
  voiceClips: HeritageVoiceClip[];
  mediaItems: HeritageMediaItem[];
  visitedVoices: ReadonlySet<string>;
  onSelectOverviewVoice: (voice: HeritageVoice) => void;
  onSelectSceneVoiceClip: (clip: HeritageVoiceClip) => void;
  onSelectMediaItem: (item: HeritageMediaItem) => void;
}) {
  const sortedClips = [...voiceClips].sort((a, b) => a.sort_order - b.sort_order);
  const sortedMedia = isOverview ? [] : [...mediaItems].sort((a, b) => a.sort_order - b.sort_order);
  const hasVoices = isOverview ? voices.length > 0 : sortedClips.length > 0;
  const hasMedia = sortedMedia.length > 0;
  const shouldDisplay = visible && (hasVoices || hasMedia);

  return (
    <div
      className={styles.mediaCarousel}
      id="mediaCarousel"
      style={{ display: shouldDisplay ? "flex" : "none" }}
    >
      <div
        className={styles.carouselViewport}
        id="carouselViewport"
      >
        <div className={styles.carouselTrack} id="carouselTrack">
          <div className={styles.voicesList} id="voicesList">
            {isOverview
              ? voices.map((voice, index) => {
                  const key = `ov:${voice.id}`;
                  const visited = visitedVoices.has(key);
                  return (
                    <div key={voice.id} className={styles.voiceItem}>
                      <button
                        type="button"
                        tabIndex={0}
                        className={`${styles.voice} ${styles.voiceActive}`}
                        id={`voice_${index + 1}`}
                        aria-label={`Listen to ${voice.name}`}
                        onClick={() => onSelectOverviewVoice(voice)}
                      >
                        <img
                          className={styles.voiceIconSvg}
                          alt=""
                          src={`${NAV_ITEMS_CDN}/items_voice.svg`}
                          aria-hidden="true"
                        />
                        <div className={styles.voiceAvatar}>
                          {voice.headshot_url && (
                            <img
                              className={styles.voiceAvatar_img}
                              id={`voiceAvatar_${index + 1}`}
                              src={voice.headshot_url}
                              alt={`Image of ${voice.name}`}
                            />
                          )}
                          {!visited && (
                            <div
                              className={`${styles.voiceRing} ${styles.ping} ${styles.rounded}`}
                              id={`voiceRing_${index + 1}`}
                            />
                          )}
                        </div>
                        <div
                          className={`${styles.voiceText} ${styles.rightToLeftText}`}
                          id={`voiceText_${index + 1}`}
                        >
                          <div className={styles.voiceText_name}>{voice.name}</div>
                          {voice.title && (
                            <div className={styles.voiceText_title}>{voice.title}</div>
                          )}
                        </div>
                      </button>
                    </div>
                  );
                })
              : sortedClips.map((clip, index) => {
                  const key = `clip:${clip.id}`;
                  const visited = visitedVoices.has(key);
                  return (
                    <div key={clip.id} className={styles.voiceItem}>
                      <button
                        type="button"
                        tabIndex={0}
                        className={`${styles.voice} ${styles.voiceActive}`}
                        id={`voice_${index + 1}`}
                        aria-label={`Listen ${clip.voice.name} talk about ${clip.bubble_text ?? ""}`}
                        onClick={() => onSelectSceneVoiceClip(clip)}
                      >
                        <img
                          className={styles.voiceIconSvg}
                          alt=""
                          src={`${NAV_ITEMS_CDN}/items_voice.svg`}
                          aria-hidden="true"
                        />
                        <div className={styles.voiceAvatar}>
                          {clip.voice.headshot_url && (
                            <img
                              className={styles.voiceAvatar_img}
                              id={`voiceAvatar_${index + 1}`}
                              src={clip.voice.headshot_url}
                              alt={`Image of ${clip.voice.name}`}
                            />
                          )}
                          {!visited && (
                            <div
                              className={`${styles.voiceRing} ${styles.ping} ${styles.rounded}`}
                              id={`voiceRing_${index + 1}`}
                            />
                          )}
                        </div>
                        <div
                          className={`${styles.voiceText} ${styles.rightToLeftText}`}
                          id={`voiceText_${index + 1}`}
                        >
                          <div className={styles.voiceText_name}>{clip.voice.name}</div>
                          {clip.voice.title && (
                            <div className={styles.voiceText_title}>{clip.voice.title}</div>
                          )}
                        </div>
                      </button>
                    </div>
                  );
                })}
          </div>

          <div className={styles.mediaList} id="mediaList">
            {sortedMedia.map((item, index) => {
              const isVideo = item.type.toLowerCase() === "video";
              return (
                <button
                  key={item.id}
                  type="button"
                  tabIndex={0}
                  className={styles.mediaCard}
                  id={`mediaItem_${index + 1}`}
                  aria-label={item.title ?? `Media ${index + 1}`}
                  onClick={() => onSelectMediaItem(item)}
                >
                  <div className={styles.mediaCardThumbWrap}>
                    <img
                      className={styles.mediaCardThumb}
                      src={item.thumb_url || item.asset_url}
                      alt={item.title ?? ""}
                    />
                    <img
                      className={styles.mediaCardTypeIcon}
                      src={`${NAV_ITEMS_CDN}/${isVideo ? "items_video.svg" : "items_photo.svg"}`}
                      alt=""
                      aria-hidden="true"
                    />
                  </div>
                  {item.title && (
                    <span className={styles.mediaCardTitle}>{item.title}</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export function InteractiveMediaCarousel({
  visible,
  highlights,
  selectedHighlightId,
  onSelectHighlight,
}: {
  visible: boolean;
  highlights: HeritageInteractiveHighlight[];
  selectedHighlightId: number | null;
  onSelectHighlight: (id: number) => void;
}) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const sorted = [...highlights].sort((a, b) => a.sort_order - b.sort_order);
  const shouldDisplay = visible && sorted.length > 0;

  return (
    <div
      className={styles.intMediaCarousel}
      id="intMediaCarousel"
      style={{ display: shouldDisplay ? "flex" : "none" }}
    >
      <button
        type="button"
        tabIndex={0}
        className={`${styles.carouselArrow} ${styles.navIconBg}`}
        id="intCarouselArrow_left"
        aria-label="Scroll left"
        onClick={() => scrollByOffset(viewportRef, -1)}
      >
        <LeftOutlined
          className={`${styles.navIcons} ${styles.carouselArrowIcon}`}
          aria-hidden="true"
        />
      </button>

      <div
        className={styles.intCarouselViewport}
        id="intCarouselViewport"
        ref={viewportRef}
      >
        <div
          className={styles.intMediaCarouselItems}
          id="intMediaCarouselItems"
        >
          {sorted.map((item, index) => {
            const active = selectedHighlightId === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`${styles.intMediaCard} ${active ? styles.intMediaCardActive : ""}`}
                id={`intHighlight_${item.id}`}
                aria-label={item.popup_title ?? `Highlight ${index + 1}`}
                aria-pressed={active}
                onClick={() => onSelectHighlight(item.id)}
              >
                {item.thumb_url ? (
                  <img
                    className={styles.intMediaCardThumb}
                    src={item.thumb_url}
                    alt={item.popup_title ?? ""}
                  />
                ) : (
                  <span className={styles.intMediaCardBadge}>{index + 1}</span>
                )}
                {item.popup_title && (
                  <span className={styles.intMediaCardTitle}>
                    {item.popup_title}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <button
        type="button"
        tabIndex={0}
        className={`${styles.carouselArrow} ${styles.navIconBg}`}
        id="intCarouselArrow_right"
        aria-label="Scroll right"
        onClick={() => scrollByOffset(viewportRef, 1)}
      >
        <RightOutlined
          className={`${styles.navIcons} ${styles.carouselArrowIcon}`}
          aria-hidden="true"
        />
      </button>
    </div>
  );
}

export function TourMediaPopups({
  activePopup,
  muted,
  onClose,
}: {
  activePopup: ActiveTourPopup;
  muted: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!activePopup) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [activePopup, onClose]);

  const isVoiceActive =
    activePopup?.kind === "overview_voice" || activePopup?.kind === "scene_voice";
  const overviewVoice =
    activePopup?.kind === "overview_voice" ? activePopup.voice : null;
  const overviewHasVideo = Boolean(overviewVoice?.intro_video_url);
  const sceneClip =
    activePopup?.kind === "scene_voice" ? activePopup.clip : null;
  const mediaItem =
    activePopup?.kind === "media_item" ? activePopup.item : null;

  return (
    <>
      <div
        className={`${styles.oVoiceBlurOverlay} ${isVoiceActive ? styles.oVoiceBlurOverlayActive : ""}`}
        id="oVoiceBlurOverlay"
        aria-hidden="true"
      />
      <div
        className={`${styles.oVoiceStage} ${isVoiceActive ? styles.oVoiceStageActive : ""}`}
        id="oVoiceStage"
        aria-hidden="true"
      />

      <div
        aria-hidden={!activePopup}
        aria-modal="true"
        className={`${styles.popUpParent} ${activePopup ? styles.popUpParentActive : ""}`}
        id="popUpParent"
      >
        <div className={styles.popUpOverlay} onClick={onClose} />

        <button
          type="button"
          className={`${styles.closeButton} ${styles.unselectable} ${styles.overflowPage_closeButton}`}
          id="default_popUp_CloseButton"
          aria-label="Close pop-up"
          onClick={onClose}
        >
          <img alt="" src={`${UI_ICONS_CDN}/icon_close.svg`} />
        </button>

        {/* Overview Voice (Static Bio without Video) */}
        <div
          aria-hidden={!(overviewVoice && !overviewHasVideo)}
          role="dialog"
          aria-label="Voices"
          className={`${styles.popUpGroup} ${styles.overviewVoicePop}`}
          id="oPopUp_Voices"
          style={{ display: overviewVoice && !overviewHasVideo ? "flex" : "none" }}
        >
          <div className={styles.oLeftGroup} id="oLeftGroup">
            {overviewVoice?.headshot_url && (
              <img
                id="oImg"
                className={styles.oImg}
                src={overviewVoice.headshot_url}
                alt={overviewVoice.name}
              />
            )}
          </div>
          <div className={styles.oRightGroup}>
            <div className={styles.oRightTextGroup} id="oRightTextGroup">
              {overviewVoice && (
                <>
                  <h2 className={styles.popUpVoiceHeading}>
                    Meet {overviewVoice.name}
                  </h2>
                  {overviewVoice.title && (
                    <p className={styles.popUpVoiceRole}>{overviewVoice.title}</p>
                  )}
                  {overviewVoice.bio && (
                    <p className={styles.popUpVoiceBio}>{overviewVoice.bio}</p>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        {/* Overview Voice (With Intro Video) */}
        <div
          aria-hidden={!(overviewVoice && overviewHasVideo)}
          role="dialog"
          aria-labelledby="ovLeftTitle"
          className={`${styles.popUpGroup} ${styles.overview_video_VoicePop}`}
          id="ovPopUp_Voices"
          style={{ display: overviewVoice && overviewHasVideo ? "flex" : "none" }}
        >
          <div id="ovVideo" className={styles.spVideo}>
            {overviewVoice?.intro_video_url && (
              <video
                key={overviewVoice.intro_video_url}
                id="ovVideoTag_html5_api"
                className={styles.popUpVideoPlayer}
                src={overviewVoice.intro_video_url}
                controls
                autoPlay
                playsInline
                muted={muted}
                crossOrigin="anonymous"
              />
            )}
          </div>
          <div className={styles.voiceCaptionSlot}>
            <div
              className={`${styles.voiceCaptionText} ${styles.rightToLeftText}`}
              id="ovCaptionText"
            />
          </div>
          <div className={`${styles.ovText} ${styles.rightToLeftText}`} id="spText">
            <div className={styles.oLeftText_parent}>
              <h2 className={styles.popUpVoiceHeading}>
                Meet <span id="ovLeftTitle">{overviewVoice?.name}</span>
              </h2>
              <div className={styles.oLeft_text}>
                <span id="ovLeftText">
                  {overviewVoice?.bio || overviewVoice?.title}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Scene Voice Clip Popup */}
        <div
          aria-hidden={!sceneClip}
          role="dialog"
          aria-labelledby="spLeftText"
          className={`${styles.popUpGroup} ${styles.sceneVoicePop}`}
          id="sPopUp_Voices"
          style={{ display: sceneClip ? "flex" : "none" }}
        >
          <div id="spVideo" className={styles.spVideo}>
            {sceneClip?.video_url && (
              <video
                key={sceneClip.video_url}
                id="spVideoTag_html5_api"
                className={styles.popUpVideoPlayer}
                src={sceneClip.video_url}
                controls
                autoPlay
                playsInline
                muted={muted}
                crossOrigin="anonymous"
              />
            )}
            {!sceneClip?.video_url && sceneClip?.audio_url && (
              <audio
                key={sceneClip.audio_url}
                src={sceneClip.audio_url}
                controls
                autoPlay
                muted={muted}
                crossOrigin="anonymous"
              />
            )}
          </div>

          <div className={styles.voiceCaptionSlot}>
            <div
              className={`${styles.voiceCaptionText} ${styles.rightToLeftText}`}
              id="spCaptionText"
            />
          </div>

          <div id="spText" className={styles.spText}>
            <h2 className={styles.spLeftText} id="spLeftText">
              {sceneClip?.voice.name}
            </h2>
            <div className={styles.spRightText} id="spRightText">
              {sceneClip?.voice.title}
            </div>
          </div>
        </div>

        {/* Multimedia Item Lightbox Popup */}
        <div
          aria-hidden={!mediaItem}
          role="dialog"
          aria-label="Multimedia"
          className={`${styles.popUpGroup} ${styles.imagePop}`}
          id="iPopUp_Items"
          style={{ display: mediaItem ? "flex" : "none" }}
        >
          <button
            type="button"
            className={`${styles.closeButton} ${styles.unselectable}`}
            id="iPopUp_CloseButton"
            aria-label="Close pop-up"
            onClick={onClose}
          >
            <img alt="" src={`${UI_ICONS_CDN}/icon_close.svg`} />
          </button>
          <div className={styles.iMediaItem} id="iMediaItem">
            {mediaItem &&
              (mediaItem.type.toLowerCase() === "video" ? (
                <video
                  key={mediaItem.asset_url}
                  className={styles.iMediaAsset}
                  src={mediaItem.asset_url}
                  controls
                  autoPlay
                  playsInline
                  muted={muted}
                  crossOrigin="anonymous"
                />
              ) : (
                <img
                  className={styles.iMediaAsset}
                  src={mediaItem.asset_url}
                  alt={mediaItem.title ?? ""}
                />
              ))}
          </div>
          <div className={styles.iText} id="iText">
            {mediaItem?.title && (
              <h3 className={styles.iTextTitle}>{mediaItem.title}</h3>
            )}
            {mediaItem?.caption && (
              <p className={styles.iTextCaption}>{mediaItem.caption}</p>
            )}
            {mediaItem?.credit && (
              <p className={styles.iTextCredit}>{mediaItem.credit}</p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
