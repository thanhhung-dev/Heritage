"use client";

import { useState } from "react";
import { Switch } from "antd";
import Link from "next/link";
import type { Badge, ExploreSubTabKey, ProfileData } from "./types";
import { BadgesSection } from "./BadgesSection";
import { ProfileEditForm } from "./ProfileEditForm";
import { EnvironmentOutlined } from "@ant-design/icons";
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
  saving?: boolean;
  onCancel?: () => void;
  onSave?: () => void;
}


function ExploreSubTabs({ active, onChange }: { active: ExploreSubTabKey; onChange: (key: ExploreSubTabKey) => void }) {
  return (
    <div className={styles.exploreSubTabs}>
      <button
        type="button"
        className={[styles.exploreSubTab, active === "recent" ? styles.exploreSubTabActive : ""].join(" ")}
        onClick={() => onChange("recent")}
      >
        Recently Explored
      </button>
      <button
        type="button"
        className={[styles.exploreSubTab, active === "journeys" ? styles.exploreSubTabActive : ""].join(" ")}
        onClick={() => onChange("journeys")}
      >
        My Journeys
      </button>
    </div>
  );
}

function RecentExploreCard({ subTab, onSubTabChange }: { subTab: ExploreSubTabKey; onSubTabChange: (key: ExploreSubTabKey) => void }) {
  return (
    <div className={styles.exploreSection}>
      <ExploreSubTabs active={subTab} onChange={onSubTabChange} />
      <div className={styles.emptyState}>
        <div className={styles.emptyIconContainer}>
          <EnvironmentOutlined className={styles.emptyIcon} />
        </div>
        <div className={styles.emptyText}>
          <h3 className={styles.emptyTitle}>No recent explorations yet</h3>
          <p className={styles.emptyDescription}>
            Start a conversation with the heritage chatbot to discover new cultural sites and save them to your journey.
            Your recently explored stories will appear here.
          </p>
        </div>
        <div className={styles.emptyActions}>
          <Link href="/chat">
            <button type="button" className={styles.buttonEmptyPrimary}>
              Start Exploring
            </button>
          </Link>
          <Link href="/library">
            <button type="button" className={styles.buttonEmptySecondary}>
              View My Journeys
            </button>
          </Link>
        </div>
      </div>
    </div>
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
  saving = false,
  onCancel = () => {},
  onSave = () => {},
}: PersonalInfoTabProps) {
  const [subTab, setSubTab] = useState<ExploreSubTabKey>("recent");

  if (!isEditing) {
    return (
      <>
        <RecentExploreCard subTab={subTab} onSubTabChange={setSubTab} />

        {/* Badges Section */}
        <BadgesSection badges={badges} />
      </>
    );
  }

  // Edit Mode: delegate the 2-column form to ProfileEditForm, keep
  // account-level toggles (display email / personalization consent) here
  // since they are saved immediately via their own handlers.
  return (
    <>
      <ProfileEditForm
        formData={formData}
        saving={saving}
        badges={badges}
        onFormChange={onFormChange}
        onCancel={onCancel}
        onSave={onSave}
      />


      <div className={styles.card}>
        <h2 className={styles.cardTitle}>Privacy</h2>
        <p className={styles.cardDescription}>Control what&apos;s visible on your profile and how we personalize it.</p>

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

