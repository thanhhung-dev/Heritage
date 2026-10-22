"use client";

import { useEffect, useState } from "react";
import { ConfigProvider, Spin, theme } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import Link from "next/link";
import { getUser, type User } from "@/lib/auth";
import { CoverImageModal } from "./CoverImageModal";
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
const PROFILE_BACKGROUND = "#121214";
const PROFILE_BORDER = "#2a2a2e";
const COVER_POSITION_KEY = "heritage.profile.cover-position";

const profileTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: ORANGE,
    colorBgContainer: PROFILE_BACKGROUND,
    colorBorder: PROFILE_BORDER,
    colorText: "#fafafa",
    colorTextSecondary: "#a1a1aa",
    colorTextPlaceholder: "#71717a",
    borderRadius: 8,
  },
  components: {
    Input: {
      colorBgContainer: PROFILE_BACKGROUND,
      colorBorder: PROFILE_BORDER,
      colorText: "#fafafa",
      colorTextPlaceholder: "#71717a",
      controlHeight: 40,
      borderRadius: 8,
      activeBorderColor: ORANGE,
      hoverBorderColor: "#52525b",
      activeShadow: "0 0 0 2px rgba(249, 115, 22, 0.15)",
    },
    Select: {
      colorBgContainer: PROFILE_BACKGROUND,
      colorBorder: PROFILE_BORDER,
      controlHeight: 40,
      borderRadius: 8,
      optionSelectedBg: "rgba(249, 115, 22, 0.15)",
    },
    Switch: {
      colorPrimary: ORANGE,
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
  const [coverModalOpen, setCoverModalOpen] = useState(false);
  const [coverSaving, setCoverSaving] = useState(false);
  const [coverPosition, setCoverPosition] = useState("50% 50%");
  const [activeTab, setActiveTab] = useState<ProfileTabKey>("personal");
  const [apiError, setApiError] = useState("");
  const [badges, setBadges] = useState<Badge[]>([]);
  const [milestones, setMilestones] = useState<MilestoneLevel[]>([]);
  const [authUser, setAuthUser] = useState<User | null>(null);

  useEffect(() => {
    // Google profile data (display name + avatar) lives in localStorage.
    setAuthUser(getUser());
    try {
      const storedPosition = window.localStorage.getItem(COVER_POSITION_KEY);
      if (storedPosition) setCoverPosition(storedPosition);
    } catch {}
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
            : "Could not load badges."),
        );
      }

      if (milestonesResult.status === "fulfilled") {
        setMilestones(milestonesResult.value);
      } else {
        setApiError((currentError) =>
          currentError ||
          (milestonesResult.reason instanceof Error
            ? milestonesResult.reason.message
            : "Could not load milestones."),
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

  const handleCoverSave = async (bannerUrl: string, position: string) => {
    setProfile((current) => (current ? { ...current, banner_url: bannerUrl } : current));
    setFormData((current) => ({ ...current, banner_url: bannerUrl }));
    setCoverPosition(position);
    setCoverModalOpen(false);
    try {
      window.localStorage.setItem(COVER_POSITION_KEY, position);
    } catch {}

    if (bannerUrl.startsWith("data:")) return;

    try {
      setCoverSaving(true);
      setApiError("");
      const updated = await updateProfile({ banner_url: bannerUrl });
      setProfile(updated);
      setFormData(updated);
    } catch (err: unknown) {
      setApiError(
        err instanceof Error ? err.message : "Could not update cover image. Please try again.",
      );
    } finally {
      setCoverSaving(false);
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

  if (!profile) return null;
  return (
    <ConfigProvider theme={profileTheme}>
      <div className={styles.page}>
        <div className={styles.container}>
          <Link href="/" className={styles.backLink}>
            <ArrowLeftOutlined /> Back
          </Link>


          <ProfileHeader
            profile={profile}
            authAvatarUrl={authUser?.avatar_url}
            authDisplayName={authUser?.display_name}
            authHandle={authUser?.username}
            isEditing={isEditing}
            saving={saving}
            coverPosition={coverPosition}
            onEdit={handleEdit}
            onManageCover={() => setCoverModalOpen(true)}
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

          <CoverImageModal
            open={coverModalOpen}
            currentUrl={profile.banner_url}
            initialPosition={coverPosition}
            saving={coverSaving}
            onClose={() => setCoverModalOpen(false)}
            onSave={handleCoverSave}
          />
        </div>
      </div>
    </ConfigProvider>
  );
}

