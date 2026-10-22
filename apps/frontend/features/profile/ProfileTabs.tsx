"use client";

import { PersonalInfoTab } from "./PersonalInfoTab";
import { MilestonesTab } from "./MilestonesTab";
import { AchievementsTab } from "./AchievementsTab";
import type { Badge, MilestoneLevel, ProfileData, ProfileTabKey } from "./types";
import styles from "./profile.module.css";

interface ProfileTabsProps {
  activeTab: ProfileTabKey;
  onTabChange: (key: ProfileTabKey) => void;
  isEditing: boolean;
  formData: Partial<ProfileData>;
  displayEmail: boolean;
  personalizationConsent: boolean;
  consentSaving: boolean;
  badges: Badge[];
  milestones: MilestoneLevel[];
  onFormChange: <K extends keyof ProfileData>(field: K, value: ProfileData[K]) => void;
  onDisplayEmailChange: (checked: boolean) => void;
  onPersonalizationConsentChange: (checked: boolean) => void;
}

const TAB_ITEMS: { key: ProfileTabKey; label: string }[] = [
  { key: "personal", label: "Personal Info" },
  { key: "milestones", label: "Milestones" },
  { key: "achievements", label: "Achievements" },
];

/** Owns tab-switching state/UI for Personal info, Milestones, and Achievements. */
export function ProfileTabs({
  activeTab,
  onTabChange,
  isEditing,
  formData,
  displayEmail,
  personalizationConsent,
  consentSaving,
  badges,
  milestones,
  onFormChange,
  onDisplayEmailChange,
  onPersonalizationConsentChange,
}: ProfileTabsProps) {
  return (
    <div className={styles.tabsWrap}>
      {!isEditing ? (
        <div className={styles.tabs} role="tablist">
          {TAB_ITEMS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.key}
              className={[styles.tab, activeTab === tab.key ? styles.tabActive : ""].join(" ")}
              onClick={() => onTabChange(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      ) : null}

      <div className={styles.tabPanel} role="tabpanel">
        {isEditing || activeTab === "personal" ? (
          <PersonalInfoTab
            isEditing={isEditing}
            formData={formData}
            displayEmail={displayEmail}
            personalizationConsent={personalizationConsent}
            consentSaving={consentSaving}
            badges={badges}
            onFormChange={onFormChange}
            onDisplayEmailChange={onDisplayEmailChange}
            onPersonalizationConsentChange={onPersonalizationConsentChange}
          />
        ) : null}

        {!isEditing && activeTab === "milestones" ? (
          <MilestonesTab milestones={milestones} />
        ) : null}

        {!isEditing && activeTab === "achievements" ? (
          <AchievementsTab badges={badges} />
        ) : null}
      </div>
    </div>
  );
}
