"use client";

import { ClockCircleOutlined, EditOutlined } from "@ant-design/icons";
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
  onEdit: () => void;
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
  onEdit,
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
  const level = profile.level || "Explorer";

  return (
    <>
      <div
        className={styles.banner}
        style={
          profile.banner_url
            ? {
                backgroundImage: `url(${profile.banner_url})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
              }
            : undefined
        }
      >
        <div className={styles.bannerMap} aria-hidden="true">
          <div className={styles.bannerMapPin} />
        </div>
        <div className={styles.bannerOverlay} />
        <div className={styles.statBadge}>
          <ClockCircleOutlined className={styles.statBadgeIcon} />
          <div className={styles.statBadgeTextCol}>
            <span className={styles.statBadgeValue}>{totalHours} Hours</span>
            <span className={styles.statBadgeLabel}>Total Hours</span>
          </div>
        </div>
      </div>

      <div className={styles.headerRow}>
        <div className={styles.avatarIdentityRow}>
          <UserAvatar
            src={avatarUrl}
            name={displayName}
            size={120}
            className={styles.avatar}
          />

          <div className={styles.identityCol}>
            {!isEditing ? (
              <span className={styles.levelPill}>★ {level} ★</span>
            ) : null}

            <div className={styles.nameRow}>
              <h1 className={styles.displayName}>{displayName}</h1>
              {!isEditing ? (
                <button
                  type="button"
                  className={styles.nameEditButton}
                  onClick={onEdit}
                  aria-label="Edit profile"
                  title="Edit profile"
                >
                  <EditOutlined aria-hidden="true" />
                </button>
              ) : null}
            </div>

            <div className={styles.metaRow}>
              {handle ? <span className={styles.handle}>@{handle}</span> : null}
              {handle && joined ? <span className={styles.metaDot}>&middot;</span> : null}
              {joined ? <span className={styles.joined}>{joined}</span> : null}
            </div>
          </div>
        </div>

        {isEditing ? (
          <div className={styles.actionsRow}>
            <button
              type="button"
              className={styles.buttonOutline}
              onClick={onCancel}
              disabled={saving}
            >
              Hủy
            </button>
            <button
              type="button"
              className={styles.buttonPrimary}
              onClick={onSave}
              disabled={saving}
            >
              {saving ? "Đang lưu..." : "Lưu thay đổi"}
            </button>
          </div>
        ) : null}
      </div>
    </>
  );
}
