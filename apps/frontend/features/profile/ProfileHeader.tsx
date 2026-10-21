"use client";

import { EditOutlined, EnvironmentOutlined, ClockCircleOutlined } from "@ant-design/icons";
import type { ProfileData } from "./types";
import styles from "./profile.module.css";

interface ProfileHeaderProps {
  profile: ProfileData;
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

export function ProfileHeader({ profile, isEditing, saving, onEdit, onCancel, onSave }: ProfileHeaderProps) {
  const initials = (profile.display_name || "Hung Thanh").trim().charAt(0).toUpperCase();
  const joined = formatJoined(profile.joined_at);
  const totalHours = profile.total_hours ?? 0;
  const level = profile.level || "Explorer";

  return (
    <>
      {isEditing ? (
        <div className={styles.editActions}>
          <button type="button" className={styles.buttonOutline} onClick={onCancel} disabled={saving}>
            Cancel
          </button>
          <button type="button" className={styles.buttonPrimary} onClick={onSave} disabled={saving}>
            {saving ? "Saving..." : "Save changes"}
          </button>
        </div>
      ) : null}

      <div
        className={styles.banner}
        style={profile.banner_url ? { backgroundImage: `url(${profile.banner_url})`, backgroundSize: "cover", backgroundPosition: "center" } : undefined}
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
          <div className={styles.avatarWrap}>
            <div className={styles.avatar}>
              {profile.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={profile.avatar_url} alt="" className={styles.avatarImage} />
              ) : (
                <span aria-hidden="true">{initials}</span>
              )}
            </div>
            <span className={styles.avatarPin}>
              <EnvironmentOutlined />
            </span>
          </div>
          <div className={styles.identityCol}>
            {!isEditing ? (
              <div className={styles.nameRow}>
                <span className={styles.levelPill}>★ {level} ★</span>
              </div>
            ) : null}
            <div className={styles.nameRow}>
              <h1 className={styles.displayName}>{profile.display_name || "Hung Thanh"}</h1>
              {isEditing ? <EditOutlined className={styles.nameEditIcon} /> : null}
            </div>
            <div className={styles.metaRow}>
              <span className={styles.handle}>@{profile.handle || "hung-thanh-1"}</span>
              {joined ? (
                <>
                  <span className={styles.metaDot}>&middot;</span>
                  <span className={styles.joined}>{joined}</span>
                </>
              ) : null}
            </div>
          </div>
        </div>

        <div className={styles.actionsRow}>
          {!isEditing ? (
            <button type="button" className={styles.buttonOutline} onClick={onEdit}>
              <EditOutlined /> Edit profile
            </button>
          ) : null}
        </div>
      </div>
    </>
  );
}
