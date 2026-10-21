"use client";

import { useMemo, type FormEvent } from "react";
import {
  EnvironmentOutlined,
  InstagramOutlined,
  LinkedinOutlined,
  TwitterOutlined,
  EditOutlined,
  PictureOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { Form, Input, Select } from "antd";
import type { Badge, ProfileData } from "./types";
import styles from "./profile.module.css";

const BIO_MAX_LENGTH = 750;

interface ProfileEditFormProps {
  formData: Partial<ProfileData>;
  saving: boolean;
  badges: Badge[];
  onFormChange: <K extends keyof ProfileData>(field: K, value: ProfileData[K]) => void;
  onCancel: () => void;
  onSave: () => void;
}

/**
 * Edit-mode form for the Personal info tab.
 * Layout: left column (70%) for personal information, right column (30%)
 * for social links. State is centralized through the shared `formData` /
 * `onFormChange` handler passed down from ProfilePage, so there are no
 * ad-hoc local field states here.
 */
export function ProfileEditForm({ formData, saving, badges, onFormChange, onCancel, onSave }: ProfileEditFormProps) {
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

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSave();
  };

  return (
    <Form layout="vertical" component="form" onSubmitCapture={handleSubmit} className={styles.editForm}>
      <div className={styles.editFormHeader}>
        <div>
          <h2 className={styles.editFormTitle}>Edit profile</h2>
          <p className={styles.cardDescription}>Update your personal information and social links.</p>
        </div>
        <div className={styles.editFormActions}>
          <button type="button" className={styles.buttonOutline} onClick={onCancel} disabled={saving}>
            Cancel
          </button>
          <button type="submit" className={styles.buttonPrimary} disabled={saving}>
            {saving ? "Saving..." : "Save changes"}
          </button>
        </div>
      </div>

      <div className={styles.editModeGrid}>
        {/* Left Column (70%): Personal Information */}
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>Personal Information</h2>
          <p className={styles.cardDescription}>Update personal information to customize your experience.</p>

          <Form.Item label="Edit handle" className={styles.formItem}>
            <Input
              placeholder="@hung-thanh-1"
              suffix={<EditOutlined />}
              value={formData.handle || ""}
              onChange={(e) => onFormChange("handle", e.target.value)}
            />
          </Form.Item>

          <Form.Item
            label="Avatar URL"
            className={styles.formItem}
            extra="Paste a direct image link to use as your profile avatar."
          >
            <Input
              placeholder="https://example.com/avatar.jpg"
              prefix={<PictureOutlined />}
              value={formData.avatar_url || ""}
              onChange={(e) => onFormChange("avatar_url", e.target.value)}
            />
          </Form.Item>

          <Form.Item
            label="Banner URL"
            className={styles.formItem}
            extra="Paste a direct image link to use as your profile banner."
          >
            <Input
              placeholder="https://example.com/banner.jpg"
              prefix={<PictureOutlined />}
              value={formData.banner_url || ""}
              onChange={(e) => onFormChange("banner_url", e.target.value)}
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
            label="Bio"
            className={styles.formItem}
            extra={
              <span className={styles.bioCounter}>
                {bioLength}/{BIO_MAX_LENGTH}
              </span>
            }
          >
            <Input.TextArea
              rows={4}
              maxLength={BIO_MAX_LENGTH}
              placeholder="Write a short bio about yourself..."
              value={formData.bio || ""}
              onChange={(e) => onFormChange("bio", e.target.value)}
            />
          </Form.Item>

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
        </div>

        {/* Right Column (30%): Social Links */}
        <div className={styles.glassCard}>
          <div className={styles.socialsHeader}>
            <div>
              <h2 className={styles.cardTitle}>Socials</h2>
              <p className={styles.cardDescription}>Connect your social media accounts.</p>
            </div>
            <button type="button" className={styles.addCustomLink}>
              <PlusOutlined /> Add custom link
            </button>
          </div>

          <Form.Item label="Instagram" className={styles.formItem}>
            <Input
              prefix={<InstagramOutlined />}
              placeholder="@username"
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
              placeholder="@username"
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
      </div>
    </Form>
  );
}
