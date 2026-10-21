"use client";

import { useEffect, useState } from "react";
import { Alert, ConfigProvider, Spin, theme } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import Link from "next/link";
import { getUser, type User } from "@/lib/auth";
import { ProfileHeader } from "./ProfileHeader";
import { ProfileTabs } from "./ProfileTabs";
import {
  getBadges,
  getMilestones,
  getPersonalizationConsent,
  getProfile,
  updatePersonalizationConsent,
  updateProfile,
} from "./profileService";
import type { Badge, MilestoneLevel, ProfileData, ProfileTabKey } from "./types";
import styles from "./profile.module.css";

const ORANGE = "#f97316";
const ACTIVE_ORANGE = "#f97316";
const PROFILE_BACKGROUND = "#171717";
const PROFILE_BORDER = "#333333";

const profileTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: ORANGE,
    colorBgContainer: PROFILE_BACKGROUND,
    colorBorder: PROFILE_BORDER,
    colorText: "#ffffff",
    colorTextSecondary: "rgba(255, 255, 255, 0.7)",
    colorTextPlaceholder: "rgba(255, 255, 255, 0.7)",
    borderRadius: 12,
  },
  components: {
    Input: {
      colorBgContainer: PROFILE_BACKGROUND,
      colorBorder: PROFILE_BORDER,
      colorText: "#ffffff",
      colorTextPlaceholder: "rgba(255, 255, 255, 0.7)",
      controlHeight: 44,
      borderRadius: 12,
      activeBorderColor: ORANGE,
      hoverBorderColor: "rgba(255, 155, 45, 0.5)",
      activeShadow: "0 0 0 2px rgba(255, 155, 45, 0.15)",
    },
    Select: {
      colorBgContainer: PROFILE_BACKGROUND,
      colorBorder: PROFILE_BORDER,
      controlHeight: 44,
      borderRadius: 12,
      optionSelectedBg: "rgba(255, 155, 45, 0.15)",
    },
    Switch: {
      colorPrimary: ORANGE,
    },
    Tabs: {
      itemColor: "rgba(255, 255, 255, 0.7)",
      itemSelectedColor: "#ffffff",
      itemHoverColor: "#ffffff",
      inkBarColor: ACTIVE_ORANGE,
      titleFontSize: 14,
    },
    Alert: {
      colorErrorBg: "#ffffff",
      colorErrorBorder: "#fecaca",
      colorError: "#dc2626",
      colorText: "#dc2626",
      colorIcon: "#dc2626",
    },
  },
};

export function ProfilePage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [formData, setFormData] = useState<Partial<ProfileData>>({});
  const [displayEmail, setDisplayEmail] = useState(false);
  const [personalizationConsent, setPersonalizationConsent] = useState(false);
  const [consentSaving, setConsentSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<ProfileTabKey>("personal");
  const [apiError, setApiError] = useState("");
  const [badges, setBadges] = useState<Badge[]>([]);
  const [milestones, setMilestones] = useState<MilestoneLevel[]>([]);
  const [authUser, setAuthUser] = useState<User | null>(null);

  useEffect(() => {
    // Google profile data (display name + avatar) lives in localStorage.
    setAuthUser(getUser());
  }, []);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      const [profileResult, consentResult, badgesResult, milestonesResult] = await Promise.allSettled([
        getProfile(),
        getPersonalizationConsent(),
        getBadges(),
        getMilestones(),
      ]);


      if (profileResult.status === "fulfilled") {
        const data = profileResult.value;
        setProfile(data);
        setFormData(data);
        setDisplayEmail(data.display_email);
      } else {
        setApiError(
          profileResult.reason instanceof Error
            ? profileResult.reason.message
            : "Could not load profile. Please try again.",
        );
      }

      if (consentResult.status === "fulfilled") {
        setPersonalizationConsent(consentResult.value.analytics_opt_in);
      } else {
        setApiError((currentError) =>
          currentError ||
          (consentResult.reason instanceof Error
            ? consentResult.reason.message
            : "Could not load personalization consent."),
        );
      }

      if (badgesResult.status === "fulfilled") {
        setBadges(badgesResult.value);
      } else {
        setApiError((currentError) =>
          currentError ||
          (badgesResult.reason instanceof Error
            ? badgesResult.reason.message
            : "Không thể tải danh sách huy hiệu."),
        );
      }

      if (milestonesResult.status === "fulfilled") {
        setMilestones(milestonesResult.value);
      } else {
        setApiError((currentError) =>
          currentError ||
          (milestonesResult.reason instanceof Error
            ? milestonesResult.reason.message
            : "Không thể tải cột mốc khám phá."),
        );
      }

      setLoading(false);
    }
    fetchData();
  }, []);


  const handleFormChange = <K extends keyof ProfileData>(field: K, value: ProfileData[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleEdit = () => {
    setIsEditing(true);
    setActiveTab("personal");
  };

  const handleCancel = () => {
    setIsEditing(false);
    setFormData(profile || {});
    setDisplayEmail(profile?.display_email || false);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setApiError("");
      const updated = await updateProfile({ ...formData, display_email: displayEmail });
      setProfile(updated);
      setFormData(updated);
      setIsEditing(false);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to save profile. Please try again.";
      setApiError(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const handlePersonalizationConsentChange = async (checked: boolean) => {
    const previousValue = personalizationConsent;
    setPersonalizationConsent(checked);
    setApiError("");
    try {
      setConsentSaving(true);
      const updated = await updatePersonalizationConsent(checked);
      setPersonalizationConsent(updated.analytics_opt_in);
    } catch (err: unknown) {
      setPersonalizationConsent(previousValue);
      setApiError(
        err instanceof Error ? err.message : "Could not update personalization consent.",
      );
    } finally {
      setConsentSaving(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <Spin size="large" />
      </div>
    );
  }

  if (!profile) {
    return (
      <ConfigProvider theme={profileTheme}>
        <div className={styles.page}>
          <div className={styles.container}>
            <Alert type="error" message={apiError || "Profile not found."} showIcon className={styles.alert} />
          </div>
        </div>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider theme={profileTheme}>
      <div className={styles.page}>
        <div className={styles.container}>
          <Link href="/" className={styles.backLink}>
            <ArrowLeftOutlined /> Back
          </Link>

          {apiError && (
            <Alert
              type="error"
              message={apiError}
              closable
              onClose={() => setApiError("")}
              className={styles.alert}
              showIcon
            />
          )}

          <ProfileHeader
            profile={profile}
            authAvatarUrl={authUser?.avatar_url}
            authDisplayName={authUser?.display_name}
            authHandle={authUser?.username}
            isEditing={isEditing}
            saving={saving}
            onEdit={handleEdit}
            onCancel={handleCancel}
            onSave={handleSave}
          />

          <ProfileTabs
            activeTab={activeTab}
            onTabChange={setActiveTab}
            isEditing={isEditing}
            formData={formData}
            displayEmail={displayEmail}
            personalizationConsent={personalizationConsent}
            consentSaving={consentSaving}
            badges={badges}
            milestones={milestones}
            onFormChange={handleFormChange}
            onDisplayEmailChange={setDisplayEmail}
            onPersonalizationConsentChange={handlePersonalizationConsentChange}
          />

        </div>
      </div>
    </ConfigProvider>
  );
}

