"use client";

import { useMemo } from "react";
import {
  EditOutlined,
  EnvironmentOutlined,
  InstagramOutlined,
  LinkedinOutlined,
  PlusOutlined,
  TwitterOutlined,
} from "@ant-design/icons";
import { Form, Input, Select, Switch } from "antd";
import type { Badge, ProfileData } from "./types";
import styles from "./profile.module.css";

const BIO_MAX_LENGTH = 750;

interface ProfileEditFormProps {
  formData: Partial<ProfileData>;
  badges: Badge[];
  displayEmail: boolean;
  personalizationConsent: boolean;
  consentSaving: boolean;
  onFormChange: <K extends keyof ProfileData>(field: K, value: ProfileData[K]) => void;
  onDisplayEmailChange: (checked: boolean) => void;
  onPersonalizationConsentChange: (checked: boolean) => void;
}

export function ProfileEditForm({
  formData,
  badges,
  displayEmail,
  personalizationConsent,
  consentSaving,
  onFormChange,
  onDisplayEmailChange,
  onPersonalizationConsentChange,
}: ProfileEditFormProps) {
  const featuredBadges = formData.featured_badges || [];
  const bioLength = formData.bio?.length ?? 0;

  const claimedBadges = useMemo(() => badges.filter((badge) => badge.is_unlocked), [badges]);

  const toggleFeaturedBadge = (badgeId: string) => {
    const isSelected = featuredBadges.includes(badgeId);
    if (isSelected) {
      onFormChange("featured_badges", featuredBadges.filter((id) => id !== badgeId));
      return;
    }
    if (featuredBadges.length >= 3) return;
    onFormChange("featured_badges", [...featuredBadges, badgeId]);
  };

  return (
    <Form layout="vertical" className={styles.editForm}>
      <div className={styles.editModeGrid}>
        <section className={styles.editSection}>
          <div className={styles.editSectionHeader}>
            <h2 className={styles.editSectionTitle}>Personal info</h2>
          </div>

          <div className={styles.editSectionBody}>
            <Form.Item label="Edit handle" className={styles.formItem}>
              <Input
                placeholder="@hung-thanh-1"
                suffix={<EditOutlined />}
                value={formData.handle || ""}
                onChange={(e) => onFormChange("handle", e.target.value)}
              />
            </Form.Item>

            <Form.Item label="Location" className={styles.formItem}>
              <div className={styles.locationRow}>
                <Select
                  placeholder="Select your country"
                  value={formData.country || undefined}
                  onChange={(value) => onFormChange("country", value)}
                  options={[
                    { value: "VN", label: "Vietnam" },
                    { value: "US", label: "United States" },
                    { value: "FR", label: "France" },
                    { value: "JP", label: "Japan" },
                  ]}
                />
                <Input
                  placeholder="e.g. San Francisco"
                  prefix={<EnvironmentOutlined />}
                  value={formData.city || ""}
                  onChange={(e) => onFormChange("city", e.target.value)}
                />
              </div>
            </Form.Item>

            <Form.Item
              label={
                <span className={styles.bioLabel}>
                  <span>Bio</span>
                  <span>
                    {bioLength}/{BIO_MAX_LENGTH}
                  </span>
                </span>
              }
              className={`${styles.formItem} ${styles.bioFormItem}`}
              extra="Max. 750 characters"
            >
              <Input.TextArea
                rows={6}
                maxLength={BIO_MAX_LENGTH}
                placeholder="Write a short bio about yourself..."
                value={formData.bio || ""}
                onChange={(e) => onFormChange("bio", e.target.value)}
              />
            </Form.Item>

            <div className={styles.inlineToggle}>
              <Switch checked={displayEmail} onChange={onDisplayEmailChange} />
              <span className={styles.toggleLabel}>Display your account email</span>
            </div>
          </div>
        </section>

        <section className={styles.editSection}>
          <div className={styles.editSectionHeader}>
            <h2 className={styles.editSectionTitle}>Socials</h2>
            <button type="button" className={styles.addCustomLink}>
              <PlusOutlined /> Add custom link
            </button>
          </div>

          <div className={styles.editSectionBody}>
            <Form.Item label="Instagram" className={styles.formItem}>
              <Input
                prefix={<InstagramOutlined />}
                placeholder="@Username"
                value={formData.socials?.instagram || ""}
                onChange={(e) =>
                  onFormChange("socials", {
                    ...formData.socials,
                    instagram: e.target.value,
                  })
                }
              />
            </Form.Item>

            <Form.Item label="LinkedIn" className={styles.formItem}>
              <Input
                prefix={<LinkedinOutlined />}
                placeholder="https://linkedin.com/in/username"
                value={formData.socials?.linkedin || ""}
                onChange={(e) =>
                  onFormChange("socials", {
                    ...formData.socials,
                    linkedin: e.target.value,
                  })
                }
              />
            </Form.Item>

            <Form.Item label="X (Twitter)" className={styles.formItem}>
              <Input
                prefix={<TwitterOutlined />}
                placeholder="@Username"
                value={formData.socials?.twitter || ""}
                onChange={(e) =>
                  onFormChange("socials", {
                    ...formData.socials,
                    twitter: e.target.value,
                  })
                }
              />
            </Form.Item>
          </div>
        </section>
      </div>

      <section className={styles.editSection}>
        <div className={styles.editSectionHeader}>
          <div>
            <h2 className={styles.editSectionTitle}>Featured badges</h2>
            <p className={styles.editSectionDescription}>
              Your first 3 claimed badges are featured automatically. Pick which ones show as
              icons next to your level.
            </p>
          </div>
        </div>

        <div className={styles.editSectionBody}>
          {claimedBadges.length === 0 ? (
            <p className={styles.claimEmpty}>Claim a badge to feature it here.</p>
          ) : (
            <div className={styles.featuredBadgesPicker}>
              {claimedBadges.map((badge) => (
                <button
                  key={badge.id}
                  type="button"
                  className={[
                    styles.featuredBadgeChip,
                    featuredBadges.includes(badge.id) ? styles.featuredBadgeChipActive : "",
                  ].join(" ")}
                  onClick={() => toggleFeaturedBadge(badge.id)}
                >
                  {badge.title}
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      <div className={styles.activitySection}>
        <h2 className={styles.editSectionTitle}>Activity</h2>
        <label className={styles.activityToggle}>
          <Switch
            checked={formData.show_activity_on_profile ?? true}
            onChange={(checked) => onFormChange("show_activity_on_profile", checked)}
          />
          <span className={styles.toggleLabel}>Show on profile</span>
        </label>
      </div>

      <section className={styles.editSection}>
        <div className={styles.editSectionHeader}>
          <div>
            <h2 className={styles.editSectionTitle}>Privacy</h2>
            <p className={styles.editSectionDescription}>
              Control how we personalize your experience.
            </p>
          </div>
        </div>

        <div className={styles.editSectionBody}>
          <div className={styles.inlineToggle}>
            <Switch
              checked={personalizationConsent}
              loading={consentSaving}
              onChange={onPersonalizationConsentChange}
            />
            <span className={styles.toggleLabel}>Personalization consent</span>
          </div>
        </div>
      </section>
    </Form>
  );
}
