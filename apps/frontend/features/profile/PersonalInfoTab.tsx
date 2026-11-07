"use client";

import Link from "next/link";
import { CompassOutlined, EnvironmentOutlined } from "@ant-design/icons";
import type { Badge, ProfileData } from "./types";
import { BadgesSection } from "./BadgesSection";
import { ProfileEditForm } from "./ProfileEditForm";
import styles from "./profile.module.css";

interface PersonalInfoTabProps {
  isEditing: boolean;
  formData: Partial<ProfileData>;
  displayEmail: boolean;
  personalizationConsent: boolean;
  consentSaving: boolean;
  badges: Badge[];
  onFormChange: <K extends keyof ProfileData>(field: K, value: ProfileData[K]) => void;
  onDisplayEmailChange: (checked: boolean) => void;
  onPersonalizationConsentChange: (checked: boolean) => void;
}

function RecentExploreCard() {
  return (
    <section className={styles.exploreSection} aria-labelledby="recent-explored-title">
      <div className={styles.sectionHeader}>
        <div className={styles.sectionHeading}>
          <h2 id="recent-explored-title" className={styles.sectionTitle}>
            Recently explored
          </h2>
          <p className={styles.cardDescription}>
            Your latest heritage discoveries will appear here.
          </p>
        </div>
        <Link href="/map" className={styles.sectionAction}>
          <CompassOutlined aria-hidden="true" />
          View map
        </Link>
      </div>

      <div className={styles.emptyState}>
        <div className={styles.emptyIconContainer}>
          <EnvironmentOutlined className={styles.emptyIcon} aria-hidden="true" />
        </div>
        <div className={styles.emptyText}>
          <h3 className={styles.emptyTitle}>No recent explorations yet</h3>
          <p className={styles.emptyDescription}>
            Start a conversation with the heritage chatbot to discover new cultural
            sites and save them to your journey.
          </p>
        </div>
        <div className={styles.emptyActions}>
          <Link href="/chat" className={styles.buttonEmptyPrimary}>
            Start Exploring
          </Link>
        </div>
      </div>
    </section>
  );
}

export function PersonalInfoTab({
  isEditing,
  formData,
  displayEmail,
  personalizationConsent,
  consentSaving,
  badges,
  onFormChange,
  onDisplayEmailChange,
  onPersonalizationConsentChange,
}: PersonalInfoTabProps) {
  if (!isEditing) {
    return (
      <>
        <RecentExploreCard />
        <BadgesSection badges={badges} />
      </>
    );
  }

  return (
    <ProfileEditForm
      formData={formData}
      badges={badges}
      displayEmail={displayEmail}
      personalizationConsent={personalizationConsent}
      consentSaving={consentSaving}
      onFormChange={onFormChange}
      onDisplayEmailChange={onDisplayEmailChange}
      onPersonalizationConsentChange={onPersonalizationConsentChange}
    />
  );
}
