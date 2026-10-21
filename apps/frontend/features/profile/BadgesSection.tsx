"use client";

import type { Badge } from "./types";
import { BadgesGrid } from "./BadgesGrid";
import styles from "./profile.module.css";

interface BadgesSectionProps {
  badges: Badge[];
}

export function BadgesSection({ badges }: BadgesSectionProps) {
  const earnedCount = badges.filter((badge) => badge.is_unlocked).length;

  return (
    <div className={styles.badgesSection}>
      <div className={styles.badgesHeader}>
        <div>
          <h2 className={styles.badgesTitle}>Badges</h2>
          <p className={styles.cardDescription}>
            Collect badges by exploring heritage, asking the chatbot, and learning local customs.
          </p>
        </div>
        <span className={styles.badgesEarnedCount}>
          {earnedCount}/{badges.length} badges earned
        </span>
      </div>
      <BadgesGrid badges={badges} />
    </div>
  );
}

