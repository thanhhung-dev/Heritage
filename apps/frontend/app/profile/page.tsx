'use client';

import React, { useEffect, useState } from 'react';
import { Playfair_Display, Inter } from 'next/font/google';
import { ConfigProvider, theme, Form, Input, Button, Switch, Select, message, Spin, Tabs } from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  EnvironmentOutlined,
  InstagramOutlined,
  LinkedinOutlined,
  TwitterOutlined,
  PlusOutlined,
  SafetyOutlined,
  TrophyOutlined,
  LockOutlined,
  StarOutlined,
  CalendarOutlined,
  SearchOutlined,
  TeamOutlined,
  BookOutlined,
  CompassOutlined,
} from '@ant-design/icons';
import styles from './page.module.css';

const playfair = Playfair_Display({ subsets: ['latin', 'vietnamese'], weight: ['600', '700'] });
const inter = Inter({ subsets: ['latin', 'vietnamese'] });

const API_BASE = 'http://127.0.0.1:8000';

export default function ProfilePage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [consent, setConsent] = useState(false);
  const [displayEmail, setDisplayEmail] = useState(false);
  const [activeTab, setActiveTab] = useState('personal');
  const [activeMilestoneLevel, setActiveMilestoneLevel] = useState('seeker');
  const [profileData, setProfileData] = useState({ display_name: 'Hung Thanh', avatar_url: '', bio: '' });

  useEffect(() => {
    async function fetchData() {
      try {
        const [resP, resC] = await Promise.all([
          fetch(`${API_BASE}/api/profile/me`),
          fetch(`${API_BASE}/api/profile/consent`)
        ]);
        if (resP.ok) {
          const p = await resP.json();
          setProfileData(p);
          form.setFieldsValue(p);
        }
        if (resC.ok) {
          const c = await resC.json();
          setConsent(c.personalization_consent);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [form]);

  const onSave = async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();
      const res = await fetch(`${API_BASE}/api/profile/me`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      if (!res.ok) throw new Error();
      message.success('Đã lưu thay đổi hồ sơ!');
      setProfileData((prev) => ({ ...prev, ...values }));
    } catch (err) {
      message.error('Lưu thất bại');
    } finally {
      setSaving(false);
    }
  };

  const onConsentToggle = async (checked: boolean) => {
    setConsent(checked);
    try {
      const res = await fetch(`${API_BASE}/api/profile/consent`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ personalization_consent: checked }),
      });
      if (!res.ok) throw new Error();
      message.success('Cập nhật quyền riêng tư thành công');
    } catch {
      setConsent(!checked);
      message.error('Không cập nhật được quyền riêng tư');
    }
  };

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#F5811F',
          colorBgContainer: '#14181F',
          colorBorder: 'rgba(255,255,255,0.12)',
          fontFamily: inter.style.fontFamily,
        },
      }}
    >
      <div className={styles.pageContainer}>
        <div className={styles.contentWrapper}>
          {/* Back to home */}
          <div className={styles.backLink}>
            <a href="/" className={styles.backLinkAnchor}>
              <ArrowLeftOutlined /> Quay lại
            </a>
          </div>

          {/* Banner */}
          <div className={styles.banner}>
            <div className={styles.bannerOverlay} />
            <div className={styles.bannerStats}>
              <div className={`${playfair.className} ${styles.bannerStatsNumber}`}>12</div>
              <div className={styles.bannerStatsLabel}>Artifacts Saved</div>
            </div>
          </div>

          {/* Profile Header Row */}
          <div className={styles.profileHeaderRow}>
            <div className={styles.profileInfo}>
              <div className={styles.avatar}>
                {profileData.avatar_url && (
                  <img src={profileData.avatar_url} alt="Avatar" className={styles.avatarImg} />
                )}
              </div>
              <div className={styles.profileDetails}>
                <div className={styles.profileNameRow}>
                  <h1 className={`${playfair.className} ${styles.profileName}`}>
                    {profileData.display_name}
                  </h1>
                  <EditOutlined className={styles.editIcon} />
                </div>
                <p className={styles.profileHandle}>@{profileData.display_name?.toLowerCase().replace(/\s+/g, '')}</p>
              </div>
            </div>

            <div className={styles.profileButtons}>
              <Button className={styles.cancelButton}>Hủy</Button>
              <Button type="primary" loading={saving} onClick={onSave} className={styles.saveButton}>
                Lưu thay đổi
              </Button>
            </div>
          </div>

          {/* Tabs */}
          <div className={styles.tabsContainer}>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={[
                { key: 'personal', label: 'Personal Info' },
                { key: 'milestones', label: 'Milestones' },
                { key: 'achievements', label: 'Achievements' },
              ]}
            />
          </div>

          {/* Personal Info Tab */}
          {activeTab === 'personal' && (
            <div className={styles.personalTabContent}>
              <div className={styles.profileGrid}>
                {/* Personal Info Card */}
                <div className={styles.glassCard}>
                  <h3 className={styles.cardTitle}>Thông tin cá nhân</h3>
                  <p className={styles.cardSubtitle}>Cập nhật hồ sơ của bạn.</p>
                  <Form form={form} layout="vertical">
                    <div className={styles.formGrid}>
                      <Form.Item label="Tên hiển thị" name="display_name">
                        <Input placeholder="Nhập tên hiển thị" />
                      </Form.Item>
                      <Form.Item label="Email" name="email">
                        <Input placeholder="example@heritage.vn" />
                      </Form.Item>
                    </div>
                    <Form.Item label="Tiểu sử" name="bio">
                      <Input.TextArea rows={3} placeholder="Chia sẻ câu chuyện của bạn..." />
                    </Form.Item>
                    <Form.Item label="Địa điểm" name="location">
                      <Input prefix={<EnvironmentOutlined />} placeholder="Thành phố, Quốc gia" />
                    </Form.Item>
                    <div className={styles.switchRow}>
                      <Switch checked={displayEmail} onChange={setDisplayEmail} />
                      <span className={styles.switchLabel}>Hiển thị email trên hồ sơ công khai</span>
                    </div>
                  </Form>
                </div>

                {/* Social Links Card */}
                <div className={styles.glassCard}>
                  <div className={styles.socialCardHeader}>
                    <h3 className={styles.socialCardTitle}>Social Links</h3>
                    <a href="#" className={styles.addCustomLink}>
                      <PlusOutlined /> Thêm
                    </a>
                  </div>
                  <div className={styles.socialInputs}>
                    <div>
                      <label className={styles.socialInputLabel}>Instagram</label>
                      <Input prefix={<InstagramOutlined />} placeholder="username" />
                    </div>
                    <div>
                      <label className={styles.socialInputLabel}>Twitter</label>
                      <Input prefix={<TwitterOutlined />} placeholder="@handle" />
                    </div>
                    <div>
                      <label className={styles.socialInputLabel}>LinkedIn</label>
                      <Input prefix={<LinkedinOutlined />} placeholder="profile URL" />
                    </div>
                  </div>
                </div>
              </div>

              {/* Privacy/Consent Card */}
              <div className={`${styles.glassCard} ${styles.consentCard}`}>
                <div className={styles.consentInfo}>
                  <h3>
                    <SafetyOutlined className={styles.consentIcon} />
                    Quyền riêng tư
                  </h3>
                  <p className={styles.consentDescription}>
                    Cho phép chúng tôi cá nhân hóa trải nghiệm của bạn với nội dung & khuyến nghị được quản lý.
                  </p>
                </div>
                <Switch checked={consent} onChange={onConsentToggle} />
              </div>
            </div>
          )}

          {/* Milestones Tab */}
          {activeTab === 'milestones' && (
            <div className={styles.milestonesTabContent}>
              {/* Header */}
              <div className={styles.milestonesHeader}>
                <h2 className={`${playfair.className} ${styles.milestonesTitle}`}>Heritage Milestones</h2>
                <p className={styles.milestonesSubtitle}>Track your journey through Vietnam's cultural treasures.</p>
              </div>

              {/* Level Navigator */}
              <div className={styles.milestonesNav}>
                {['seeker', 'explorer', 'pathfinder', 'ambassador'].map((level) => (
                  <button
                    key={level}
                    onClick={() => setActiveMilestoneLevel(level)}
                    className={`${styles.milestoneButton} ${activeMilestoneLevel === level ? styles.milestoneButtonActive : ''}`}
                  >
                    {level === 'seeker' && 'Heritage Seeker'}
                    {level === 'explorer' && 'Culture Scholar'}
                    {level === 'pathfinder' && 'Journey Pathfinder'}
                    {level === 'ambassador' && 'Heritage Ambassador'}
                  </button>
                ))}
              </div>

              {/* Seeker Level */}
              {activeMilestoneLevel === 'seeker' && (
                <div className={`${styles.glassCard} ${styles.milestoneDetailCard}`}>
                  <div className={styles.milestoneDetailHeader}>
                    <SearchOutlined className={styles.milestoneIcon} style={{ color: '#F5811F' }} />
                    <div className={styles.milestoneDetailInfo}>
                      <h2 className={playfair.className}>Heritage Seeker</h2>
                      <p className={styles.milestoneProgress}>3 / 3 milestones completed ✓</p>
                    </div>
                  </div>
                  <p className={styles.milestoneDescription}>
                    Begin your journey by exploring core features and discovering the richness of Vietnamese heritage.
                  </p>

                  <div className={styles.milestonesGrid}>
                    <div className={styles.milestoneItem}>
                      <div className={styles.milestoneItemHeader}>
                        <h4 className={styles.milestoneItemTitle}>✅ First Explore</h4>
                        <span className={`${styles.milestoneItemStatus} ${styles.statusCompleted}`}>Completed</span>
                      </div>
                      <p className={styles.milestoneItemDescription}>Visit the Explore page and learn about 1 artifact.</p>
                    </div>
                    <div className={styles.milestoneItem}>
                      <div className={styles.milestoneItemHeader}>
                        <h4 className={styles.milestoneItemTitle}>✅ Personal Touch</h4>
                        <span className={`${styles.milestoneItemStatus} ${styles.statusCompleted}`}>Completed</span>
                      </div>
                      <p className={styles.milestoneItemDescription}>Complete your profile by adding a bio and avatar.</p>
                    </div>
                    <div className={styles.milestoneItem}>
                      <div className={styles.milestoneItemHeader}>
                        <h4 className={styles.milestoneItemTitle}>✅ Bookmarked</h4>
                        <span className={`${styles.milestoneItemStatus} ${styles.statusCompleted}`}>Completed</span>
                      </div>
                      <p className={styles.milestoneItemDescription}>Save 3 artifacts to your collection for later.</p>
                    </div>
                  </div>

                  <div className={styles.milestoneFooterText}>
                    <p>Complete this level to unlock Culture Scholar milestones.</p>
                  </div>
                </div>
              )}

              {/* Explorer Level */}
              {activeMilestoneLevel === 'explorer' && (
                <div className={`${styles.glassCard} ${styles.milestoneDetailCard}`}>
                  <div className={styles.milestoneDetailHeader}>
                    <BookOutlined className={styles.milestoneIcon} style={{ color: '#F5811F' }} />
                    <div className={styles.milestoneDetailInfo}>
                      <h2 className={playfair.className}>Culture Scholar</h2>
                      <p className={styles.milestoneProgress}>1 / 3 milestones completed</p>
                    </div>
                  </div>
                  <p className={styles.milestoneDescription}>
                    Deepen your connection by engaging with content, sharing discoveries, and joining the community.
                  </p>

                  <div className={styles.milestonesGrid}>
                    <div className={styles.milestoneItem}>
                      <div className={styles.milestoneItemHeader}>
                        <h4 className={styles.milestoneItemTitle}>✅ Interactive Learner</h4>
                        <span className={`${styles.milestoneItemStatus} ${styles.statusCompleted}`}>Completed</span>
                      </div>
                      <p className={styles.milestoneItemDescription}>Engage with 3D models or interactive features on 5 artifacts.</p>
                    </div>
                    <div className={styles.milestoneItem}>
                      <div className={styles.milestoneItemHeader}>
                        <h4 className={styles.milestoneItemTitle}>🔒 Social Connector</h4>
                        <span className={`${styles.milestoneItemStatus} ${styles.statusLocked}`}>Locked</span>
                      </div>
                      <p className={styles.milestoneItemDescription}>Share 2 artifacts on social media.</p>
                    </div>
                    <div className={styles.milestoneItem}>
                      <div className={styles.milestoneItemHeader}>
                        <h4 className={styles.milestoneItemTitle}>🔒 Community Voice</h4>
                        <span className={`${styles.milestoneItemStatus} ${styles.statusLocked}`}>Locked</span>
                      </div>
                      <p className={styles.milestoneItemDescription}>Write a comment or join a discussion thread.</p>
                    </div>
                  </div>

                  <div className={styles.milestoneFooterText}>
                    <p>Complete this level to unlock Journey Pathfinder milestones.</p>
                  </div>
                </div>
              )}

              {/* Pathfinder Level (Locked) */}
              {activeMilestoneLevel === 'pathfinder' && (
                <div className={`${styles.glassCard} ${styles.lockedCard}`}>
                  <div className={styles.lockedCardContent}>
                    <div className={styles.lockedCardInfo}>
                      <h3>🔒 Journey Pathfinder</h3>
                      <p>Connect heritage sites through meaningful cultural journeys.</p>
                    </div>
                    <span className={styles.lockedCardRequirement}>Unlock Culture Scholar first</span>
                  </div>
                </div>
              )}

              {/* Ambassador Level (Locked) */}
              {activeMilestoneLevel === 'ambassador' && (
                <div className={`${styles.glassCard} ${styles.lockedCard}`}>
                  <div className={styles.lockedCardContent}>
                    <div className={styles.lockedCardInfo}>
                      <h3>🔒 Heritage Ambassador</h3>
                      <p>Explore for 7 days in a row and share the cultural stories you discover.</p>
                    </div>
                    <span className={styles.lockedCardRequirement}>Unlock Journey Pathfinder first</span>
                  </div>
                </div>
              )}

              <div className={styles.milestoneFooterText}>
                <p>Keep exploring, each milestone celebrates a new step in your heritage journey.</p>
              </div>
            </div>
          )}

          {/* Achievements Tab */}
          {activeTab === 'achievements' && (
            <div className={`${styles.glassCard} ${styles.achievementsTabContent}`}>
              <TrophyOutlined className={styles.achievementsIcon} />
              <h2 className={`${playfair.className} ${styles.achievementsTitle}`}>Achievements & Badges</h2>
              <p className={styles.achievementsDescription}>Hoàn thành các cột mốc di sản để mở khóa huy hiệu danh giá.</p>
            </div>
          )}
        </div>
      </div>
    </ConfigProvider>
  );
}
