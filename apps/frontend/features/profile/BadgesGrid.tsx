"use client";

import { LockOutlined } from "@ant-design/icons";
import type { Badge } from "./types";
import { getBadgeIcon } from "./profileData";
import styles from "./profile.module.css";

interface BadgesGridProps {
  badges: Badge[];
}

/**
 * Renders the gamification Badges grid (6 columns, responsive).
 * Locked badges (is_unlocked === false) are dimmed to 0.4 opacity and
 * show a lock icon in the top-right corner. Unlocked badges render at
 * full brightness with their earned icon (resolved from `icon_key` via
 * `getBadgeIcon`).
 */
export function BadgesGrid({ badges }: BadgesGridProps) {
  return (
    <div className={styles.badgesGrid}>
      {badges.map((badge) => (
        <div
          key={badge.id}
          className={[styles.badgeCard, badge.is_unlocked ? "" : styles.badgeCardLocked].join(" ")}
        >
          {!badge.is_unlocked ? (
            <span className={styles.badgeCornerIcon}>
              <LockOutlined />
            </span>
          ) : null}
          <span className={styles.badgeIcon} aria-hidden="true">
            {getBadgeIcon(badge.icon_key)}
          </span>
          <div className={styles.badgeLabel}>{badge.title}</div>
          <div className={styles.badgeDescription}>{badge.description}</div>
        </div>
      ))}
    </div>
  );
}

