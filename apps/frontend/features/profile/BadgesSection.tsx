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
    <section className={styles.badgesSection}>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionHeading}>
          <h2 className={styles.sectionTitle}>Badges</h2>
          <p className={styles.cardDescription}>
            Badges you earn automatically as you build. Claim them to show them off.
          </p>
        </div>
        <span className={styles.badgesEarnedCount}>
          {earnedCount} of {badges.length} earned
        </span>
      </div>
      <BadgesGrid badges={badges} />
    </section>
  );
}
