"use client";

import { Tabs } from "antd";
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
    <Tabs
      activeKey={activeTab}
      onChange={(key) => onTabChange(key as ProfileTabKey)}
      className={styles.tabs}
      items={[
        {
          key: "personal",
          label: "Personal Info",
          children: (
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
          ),
        },
        {
          key: "milestones",
          label: "Milestones",
          children: <MilestonesTab milestones={milestones} />,
        },
        {
          key: "achievements",
          label: "Achievements",
          children: <AchievementsTab badges={badges} />,
        },
      ]}
    />
  );
}
