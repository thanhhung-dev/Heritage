"use client";

import { TrophyOutlined } from "@ant-design/icons";
import type { Badge } from "./types";
import { getBadgeIcon } from "./profileData";
import styles from "./profile.module.css";

interface AchievementsTabProps {
  badges: Badge[];
}

function formatEarnedDate(earnedAt?: string | null): string {
  if (!earnedAt) return "";
  const date = new Date(earnedAt);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/**
 * Achievements tab — a full-detail view of the same badge catalogue shown in
 * the Badges section of Personal info, with earned dates and locked/unlocked
 * state driven entirely by the real `GET /api/profile/badges` response.
 */
export function AchievementsTab({ badges }: AchievementsTabProps) {
  const earnedCount = badges.filter((badge) => badge.is_unlocked).length;

  if (badges.length === 0) {
    return (
      <div className={[styles.card, styles.achievementsPlaceholder].join(" ")}>
        <TrophyOutlined className={styles.achievementsIcon} />
        <h2 className={styles.achievementsTitle}>Achievements & Badges</h2>
        <p className={styles.achievementsDescription}>
          Complete heritage milestones to unlock prestigious achievement badges.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.badgesSection}>
      <div className={styles.badgesHeader}>
        <div>
          <h2 className={styles.badgesTitle}>Achievements & Badges</h2>
          <p className={styles.cardDescription}>
            Every badge you have unlocked (and the ones still waiting) in one place.
          </p>
        </div>
        <span className={styles.badgesEarnedCount}>
          {earnedCount}/{badges.length} badges earned
        </span>
      </div>

      <div className={styles.achievementsList}>
        {badges.map((badge) => (
          <div
            key={badge.id}
            className={[styles.achievementRow, badge.is_unlocked ? "" : styles.achievementRowLocked].join(" ")}
          >
            <span className={styles.achievementIcon} aria-hidden="true">
              {getBadgeIcon(badge.icon_key)}
            </span>
            <div className={styles.achievementInfo}>
              <div className={styles.achievementTitle}>{badge.title}</div>
              <div className={styles.achievementDescription}>{badge.description}</div>
            </div>
            <span className={badge.is_unlocked ? styles.achievementStatus : styles.achievementStatusLocked}>
              {badge.is_unlocked ? `Earned ${formatEarnedDate(badge.earned_at)}` : "Locked"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

