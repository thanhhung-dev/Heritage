"use client";

import { LockOutlined } from "@ant-design/icons";
import type { Badge } from "./types";
import { getBadgeIcon } from "./profileData";
import styles from "./profile.module.css";

interface BadgesGridProps {
  badges: Badge[];
}

/**
 * Renders the gamification Badges grid (2 / 4 / 5 columns, responsive).
 * Locked badges (is_unlocked === false) are dimmed and show a lock icon in
 * the top-right corner of the artwork plate. Unlocked badges render their
 * earned icon (resolved from `icon_key` via `getBadgeIcon`).
 */
export function BadgesGrid({ badges }: BadgesGridProps) {
  return (
    <div className={styles.badgesGrid}>
      {badges.map((badge) => (
        <div
          key={badge.id}
          className={[styles.badgeCard, badge.is_unlocked ? "" : styles.badgeCardLocked].join(" ")}
        >
          <div className={styles.badgeArtCard}>
            {!badge.is_unlocked ? (
              <span className={styles.badgeCornerIcon} aria-hidden="true">
                <LockOutlined />
              </span>
            ) : null}
            <span
              className={[styles.badgeIcon, badge.is_unlocked ? "" : styles.badgeIconLocked].join(" ")}
              aria-hidden="true"
            >
              {getBadgeIcon(badge.icon_key)}
            </span>
            <span className={styles.badgeSpacer} aria-hidden="true" />
          </div>

          <div className={styles.badgeMeta}>
            <h3 className={styles.badgeLabel}>{badge.title}</h3>
            <p className={styles.badgeDescription}>{badge.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
