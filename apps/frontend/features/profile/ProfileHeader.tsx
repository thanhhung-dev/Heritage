"use client";

import {
  CameraOutlined,
  EditOutlined,
  ExpandOutlined,
  PictureOutlined,
} from "@ant-design/icons";
import { UserAvatar } from "@/features/account/UserAvatar";
import type { ProfileData } from "./types";
import styles from "./profile.module.css";

interface ProfileHeaderProps {
  profile: ProfileData;
  /** Google avatar from the stored session, used when the profile has none. */
  authAvatarUrl?: string | null;
  /** Google display name from the stored session. */
  authDisplayName?: string | null;
  /** Account username, used as a handle fallback. */
  authHandle?: string | null;
  isEditing: boolean;
  saving: boolean;
  coverPosition?: string;
  onEdit: () => void;
  onManageCover: () => void;
  onCancel: () => void;
  onSave: () => void;
}

function formatJoined(joinedAt?: string): string {
  if (!joinedAt) return "";
  const date = new Date(joinedAt);
  if (Number.isNaN(date.getTime())) return "";
  return `Joined ${date.toLocaleDateString("en-US", { month: "long", year: "numeric" })}`;
}

export function ProfileHeader({
  profile,
  authAvatarUrl,
  authDisplayName,
  authHandle,
  isEditing,
  saving,
  coverPosition = "50% 50%",
  onEdit,
  onManageCover,
  onCancel,
  onSave,
}: ProfileHeaderProps) {
  const displayName =
    profile.display_name?.trim() ||
    authDisplayName?.trim() ||
    profile.handle?.trim() ||
    "Heritage Explorer";
  const avatarUrl = profile.avatar_url?.trim() || authAvatarUrl?.trim() || "";
  const handle = (profile.handle?.trim() || authHandle?.trim() || "").replace(/^@+/, "");
  const joined = formatJoined(profile.joined_at);
  const totalHours = profile.total_hours ?? 0;
  const level = profile.level?.trim() || "Explorer";

  return (
    <>
      <div
        className={styles.banner}
        style={
          profile.banner_url
            ? {
                backgroundImage: `url(${profile.banner_url})`,
                backgroundSize: "cover",
                backgroundPosition: coverPosition,
              }
            : undefined
        }
      >
        {!profile.banner_url ? (
          <div className={styles.bannerMap} aria-hidden="true">
            <div className={styles.bannerMapPin} />
          </div>
        ) : null}
        <div className={styles.bannerOverlay} />

        {!isEditing ? (
          <div className={styles.coverActions}>
            <span className={styles.coverScrim} aria-hidden="true" />
            <button type="button" className={styles.coverAction} onClick={onManageCover}>
              <PictureOutlined aria-hidden="true" />
              Replace Image
            </button>
            <button type="button" className={styles.coverAction} onClick={onManageCover}>
              <ExpandOutlined aria-hidden="true" />
              Reposition
            </button>
          </div>
        ) : null}
      </div>

      <div className={styles.headerRow}>
        <div className={styles.avatarWrap}>
          <UserAvatar
            src={avatarUrl}
            name={displayName}
            size={144}
            className={styles.avatar}
          />
          {!isEditing ? (
            <div className={styles.avatarOverlay}>
              <button
                type="button"
                className={styles.avatarEditButton}
                onClick={onEdit}
                aria-label="Edit profile photo"
                title="Edit profile photo"
              >
                <CameraOutlined aria-hidden="true" />
              </button>
            </div>
          ) : null}
        </div>

        <div className={styles.headerContent}>
          <div className={styles.identityCol}>
            {!isEditing ? <span className={styles.levelPill}>{level}</span> : null}
            <h1 className={styles.displayName}>{displayName}</h1>
          </div>

          {isEditing ? (
            <div className={styles.actionsRow}>
              <button
                type="button"
                className={styles.buttonOutline}
                onClick={onCancel}
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="button"
                className={styles.buttonPrimary}
                onClick={onSave}
                disabled={saving}
              >
                {saving ? "Saving..." : "Save changes"}
              </button>
            </div>
          ) : (
            <div className={styles.actionsRow}>
              <button
                type="button"
                className={styles.editIconButton}
                onClick={onEdit}
                aria-label="Edit profile"
                title="Edit profile"
              >
                <EditOutlined aria-hidden="true" />
              </button>
              <button type="button" className={styles.editButton} onClick={onEdit}>
                <EditOutlined aria-hidden="true" />
                Edit profile
              </button>
            </div>
          )}
        </div>
      </div>

      <div className={styles.metaRow}>
        {handle ? <span className={styles.handle}>@{handle}</span> : null}
        {handle && joined ? <span className={styles.metaDot}>&middot;</span> : null}
        {joined ? <span className={styles.joined}>{joined}</span> : null}
        {totalHours > 0 ? (
          <>
            <span className={styles.metaDot}>&middot;</span>
            <span className={styles.joined}>{totalHours} hours explored</span>
          </>
        ) : null}
      </div>
    </>
  );
}
