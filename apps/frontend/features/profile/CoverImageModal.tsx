"use client";

import { useEffect, useRef, useState } from "react";
import {
  CheckOutlined,
  CloseOutlined,
  DragOutlined,
  PictureOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import styles from "./profile.module.css";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"];
const COVER_TEMPLATES = [1, 2, 3, 4, 5, 6].map((index) => `/covers/cover-${index}.svg`);
const DEFAULT_POSITION = { x: 50, y: 50 };

interface CoverPosition {
  x: number;
  y: number;
}

interface CoverImageModalProps {
  open: boolean;
  currentUrl?: string;
  initialPosition?: string;
  saving?: boolean;
  onClose: () => void;
  onSave: (bannerUrl: string, position: string) => void;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function parsePosition(value?: string): CoverPosition {
  if (!value) return DEFAULT_POSITION;
  const [rawX, rawY] = value.split(" ");
  const x = Number.parseFloat(rawX);
  const y = Number.parseFloat(rawY);
  return {
    x: Number.isFinite(x) ? clamp(x, 0, 100) : DEFAULT_POSITION.x,
    y: Number.isFinite(y) ? clamp(y, 0, 100) : DEFAULT_POSITION.y,
  };
}

export function CoverImageModal({
  open,
  currentUrl,
  initialPosition,
  saving = false,
  onClose,
  onSave,
}: CoverImageModalProps) {
  const [previewUrl, setPreviewUrl] = useState("");
  const [position, setPosition] = useState<CoverPosition>(DEFAULT_POSITION);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const dialogRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
    width: number;
    height: number;
  } | null>(null);

  useEffect(() => {
    if (!open) return;
    setPreviewUrl(currentUrl?.trim() || "");
    setPosition(parsePosition(initialPosition));
    setDragging(false);
    setError("");
  }, [open, currentUrl, initialPosition]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialogRef.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const isUploadedPreview = previewUrl.startsWith("data:");

  const handleFile = (file?: File) => {
    setError("");
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError("Choose a PNG, JPG, GIF or WebP image.");
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      setError("Image must be 5 MB or smaller.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        setPreviewUrl(reader.result);
        setPosition(DEFAULT_POSITION);
      }
    };
    reader.onerror = () => setError("Could not read that image. Try another file.");
    reader.readAsDataURL(file);
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!previewUrl) return;
    const rect = event.currentTarget.getBoundingClientRect();
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: position.x,
      originY: position.y,
      width: rect.width,
      height: rect.height,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const offsetX = ((event.clientX - drag.startX) / drag.width) * 100;
    const offsetY = ((event.clientY - drag.startY) / drag.height) * 100;
    setPosition({
      x: Math.round(clamp(drag.originX + offsetX, 0, 100)),
      y: Math.round(clamp(drag.originY + offsetY, 0, 100)),
    });
  };

  const endDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    dragRef.current = null;
    setDragging(false);
  };

  const handleSave = () => {
    if (!previewUrl) {
      setError("Choose a cover or upload an image first.");
      return;
    }
    const resolvedUrl = previewUrl.startsWith("/")
      ? new URL(previewUrl, window.location.origin).toString()
      : previewUrl;
    onSave(resolvedUrl, `${position.x}% ${position.y}%`);
  };

  return (
    <div
      className={styles.modalOverlay}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="cover-modal-title"
        tabIndex={-1}
      >
        <div className={styles.modalHeader}>
          <div>
            <h2 id="cover-modal-title" className={styles.modalTitle}>
              Update cover image
            </h2>
            <p className={styles.modalDescription}>
              Choose one of our cover templates or upload your own
            </p>
          </div>
          <button
            type="button"
            className={styles.modalClose}
            onClick={onClose}
            aria-label="Close"
          >
            <CloseOutlined aria-hidden="true" />
          </button>
        </div>

        <div className={styles.modalBody}>
          <div
            className={`${styles.coverPreview} ${previewUrl ? "" : styles.coverPreviewEmpty} ${
              dragging ? styles.coverPreviewDragging : ""
            }`}
            style={
              previewUrl
                ? {
                    backgroundImage: `url(${previewUrl})`,
                    backgroundPosition: `${position.x}% ${position.y}%`,
                  }
                : undefined
            }
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={endDrag}
            onPointerCancel={endDrag}
          >
            {previewUrl ? (
              <span className={styles.coverPreviewHint}>
                <DragOutlined aria-hidden="true" />
                Drag to reposition
              </span>
            ) : (
              <span className={styles.coverPreviewPlaceholder}>
                <PictureOutlined aria-hidden="true" />
                No cover selected
              </span>
            )}
          </div>

          <div className={styles.coverDivider}>
            <span>Choose a cover</span>
          </div>

          <div className={styles.coverGrid}>
            <label
              className={`${styles.coverTile} ${styles.coverUpload} ${
                isUploadedPreview ? styles.coverTileActive : ""
              }`}
            >
              <input
                type="file"
                accept={ACCEPTED_TYPES.join(",")}
                className={styles.coverFileInput}
                onChange={(event) => {
                  handleFile(event.target.files?.[0]);
                  event.target.value = "";
                }}
              />
              <UploadOutlined aria-hidden="true" />
              <span>Upload image</span>
              {isUploadedPreview ? (
                <span className={styles.coverCheck}>
                  <CheckOutlined aria-hidden="true" />
                </span>
              ) : null}
            </label>

            {COVER_TEMPLATES.map((template, index) => {
              const isSelected = previewUrl === template;
              return (
                <button
                  key={template}
                  type="button"
                  className={`${styles.coverTile} ${isSelected ? styles.coverTileActive : ""}`}
                  style={{ backgroundImage: `url(${template})` }}
                  onClick={() => {
                    setPreviewUrl(template);
                    setError("");
                  }}
                  aria-label={`Use cover template ${index + 1}`}
                  aria-pressed={isSelected}
                >
                  {isSelected ? (
                    <span className={styles.coverCheck}>
                      <CheckOutlined aria-hidden="true" />
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>

          <p className={styles.coverHint}>PNG, JPG, GIF or WebP (up to 5 MB)</p>
          {error ? <p className={styles.modalError}>{error}</p> : null}
        </div>

        <div className={styles.modalFooter}>
          <button
            type="button"
            className={styles.modalButtonSecondary}
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </button>
          <button
            type="button"
            className={styles.modalButtonPrimary}
            onClick={handleSave}
            disabled={saving || !previewUrl}
          >
            {saving ? "Saving..." : "Save changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
