"use client";

import { Switch } from "antd";
import Link from "next/link";
import { EnvironmentOutlined } from "@ant-design/icons";
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
      <div className={styles.exploreHeader}>
        <div>
          <h2 id="recent-explored-title" className={styles.exploreTitle}>
            Recently explored
          </h2>
          <p className={styles.cardDescription}>
            Your latest heritage discoveries will appear here.
          </p>
        </div>
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

  // Edit mode keeps account-level toggles here because they save immediately
  // through their own handlers. Save/Cancel live in ProfileHeader.
  return (
    <>
      <ProfileEditForm formData={formData} badges={badges} onFormChange={onFormChange} />

      <div className={styles.card}>
        <h2 className={styles.cardTitle}>Privacy</h2>
        <p className={styles.cardDescription}>
          Control what&apos;s visible on your profile and how we personalize it.
        </p>

        <div className={styles.toggleRow}>
          <Switch checked={displayEmail} onChange={onDisplayEmailChange} />
          <span className={styles.toggleLabel}>Display your account email</span>
        </div>
        <div className={styles.toggleRow}>
          <Switch
            checked={personalizationConsent}
            loading={consentSaving}
            onChange={onPersonalizationConsentChange}
          />
          <span className={styles.toggleLabel}>Personalization consent</span>
        </div>
        <div className={styles.toggleRow}>
          <span className={styles.toggleLabel}>Show activity on profile</span>
          <Switch
            checked={formData.show_activity_on_profile ?? true}
            onChange={(checked) => onFormChange("show_activity_on_profile", checked)}
          />
        </div>
      </div>
    </>
  );
}
