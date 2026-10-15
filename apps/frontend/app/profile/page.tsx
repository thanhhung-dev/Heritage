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
      <div style={{ minHeight: '100vh', background: '#0A0A0A', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
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
          colorBgContainer: 'rgba(255,255,255,0.03)',
          colorBorder: 'rgba(255,255,255,0.08)',
          borderRadius: 12,
          fontFamily: inter.style.fontFamily,
        },
        components: {
          Input: {
            colorBgContainer: 'rgba(0,0,0,0.35)',
            colorBorder: 'rgba(255,255,255,0.1)',
            colorText: '#F5F0E8',
            colorTextPlaceholder: 'rgba(255,255,255,0.3)',
            controlHeight: 44,
            borderRadius: 12,
            activeBorderColor: '#F5811F',
            hoverBorderColor: 'rgba(245,129,31,0.5)',
          },
          Select: {
            colorBgContainer: 'rgba(0,0,0,0.35)',
            colorBorder: 'rgba(255,255,255,0.1)',
            controlHeight: 44,
            borderRadius: 12,
          },
          Button: {
            borderRadius: 10,
            controlHeight: 42,
          },
          Switch: {
            colorPrimary: '#F5811F',
          },
          Tabs: {
            itemColor: 'rgba(255,255,255,0.5)',
            itemSelectedColor: '#F5F0E8',
            itemHoverColor: '#F5F0E8',
            inkBarColor: '#F5811F',
            titleFontSize: 15,
          },
        }
      }}
    >
      <div style={{ minHeight: '100vh', background: '#0A0A0A', backgroundImage: 'radial-gradient(circle at 50% 20%, rgba(232,93,4,0.12) 0%, transparent 60%)', color: '#F5F0E8', paddingBottom: '80px', paddingTop: '24px' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 24px' }}>
          
          <div style={{ marginBottom: '20px' }}>
            <a href="/" style={{ color: 'rgba(255,255,255,0.6)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <ArrowLeftOutlined /> Back
            </a>
          </div>

          <div style={{ 
            position: 'relative', 
            height: '200px', 
            borderRadius: '20px', 
            overflow: 'hidden', 
            marginBottom: '60px',
            backgroundImage: 'url(https://images.unsplash.com/photo-1528127269322-539801943592?w=1600)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}>
            <div style={{ 
              position: 'absolute', 
              inset: 0, 
              background: 'linear-gradient(135deg, rgba(232,93,4,0.3) 0%, rgba(26,10,0,0.8) 50%, rgba(10,10,10,0.95) 100%)',
            }}></div>
            <div style={{ position: 'absolute', top: '32px', left: '40px', zIndex: 1 }}>
              <div className={playfair.className} style={{ fontSize: '56px', fontWeight: 700, color: '#F5F0E8', lineHeight: 1, textShadow: '0 4px 12px rgba(0,0,0,0.5)' }}>6</div>
              <div style={{ fontSize: '15px', color: 'rgba(245,240,232,0.95)', marginTop: '8px', fontWeight: 500, letterSpacing: '0.5px' }}>Total Hours</div>
            </div>
          </div>

          <div className="profile-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: '-60px', marginBottom: '32px', flexWrap: 'wrap', gap: '24px', position: 'relative', zIndex: 10 }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '20px' }}>
              <div style={{ 
                width: '120px', 
                height: '120px', 
                borderRadius: '50%', 
                background: 'linear-gradient(135deg, #E85D04, #F5811F)', 
                border: '6px solid #0A0A0A', 
                flexShrink: 0, 
                overflow: 'hidden',
                boxShadow: '0 8px 32px rgba(232,93,4,0.3), 0 0 0 1px rgba(255,255,255,0.1) inset',
              }}>
                {profileData.avatar_url ? <img src={profileData.avatar_url} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : null}
              </div>
              <div style={{ paddingBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <h1 className={playfair.className} style={{ fontSize: '36px', fontWeight: 700, color: '#F5F0E8', margin: 0, lineHeight: 1.2 }}>
                    {profileData.display_name || 'Hung Thanh'}
                  </h1>
                  <EditOutlined style={{ color: 'rgba(255,255,255,0.5)', cursor: 'pointer', fontSize: '18px' }} />
                </div>
                <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '15px', marginTop: '6px', fontWeight: 500 }}>@hung-thanh-1</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', paddingBottom: '8px' }}>
              <Button style={{ 
                background: 'transparent', 
                border: '1px solid rgba(255,255,255,0.2)', 
                color: '#F5F0E8', 
                height: '44px', 
                borderRadius: '12px',
                fontWeight: 500,
                backdropFilter: 'blur(8px)',
              }}>Cancel</Button>
              <Button onClick={onSave} loading={saving} style={{ 
                background: 'linear-gradient(135deg, #F5811F 0%, #E85D04 100%)', 
                border: 'none', 
                color: '#1A0A00', 
                fontWeight: 700, 
                height: '44px', 
                borderRadius: '12px', 
                padding: '0 32px',
                boxShadow: '0 4px 16px rgba(232,93,4,0.4)',
              }}>Save changes</Button>
            </div>
          </div>

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              { key: 'personal', label: 'Personal info' },
              { key: 'milestones', label: 'Milestones' },
              { key: 'achievements', label: <span>Achievements <LockOutlined style={{ fontSize: '12px' }} /></span> },
            ]}
            style={{ marginBottom: '24px' }}
          />

          {activeTab === 'personal' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '28px' }}>
                <div style={{ 
                  background: 'rgba(26,26,26,0.4)', 
                  backdropFilter: 'blur(16px)', 
                  border: '1px solid rgba(255,255,255,0.05)', 
                  borderRadius: '20px', 
                  padding: '36px',
                  boxShadow: '0 8px 32px rgba(0,0,0,0.4), 0 1px 2px rgba(255,255,255,0.05) inset',
                }}>
                  <h2 className={playfair.className} style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px', color: '#F5F0E8' }}>Personal Information</h2>
                  <p style={{ color: 'rgba(255,255,255,0.5)', marginBottom: '24px', fontSize: '13px' }}>Cập nhật thông tin cá nhân để cá nhân hóa trải nghiệm.</p>
                  <Form form={form} layout="vertical">
                    <Form.Item label="Edit handle" name="display_name" rules={[{ required: true, message: 'Vui lòng nhập tên!' }]}>
                      <Input placeholder="@hung-thanh-1" suffix={<EditOutlined />} />
                    </Form.Item>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                      <Form.Item label="Location" name="country">
                        <Select placeholder="Select country" options={[{ value: 'VN', label: 'Vietnam' }, { value: 'US', label: 'United States' }]} />
                      </Form.Item>
                      <Form.Item label=" " name="city">
                        <Input placeholder="e.g. San Francisco" prefix={<EnvironmentOutlined />} />
                      </Form.Item>
                    </div>

                    <Form.Item label="Bio" name="bio">
                      <Input.TextArea rows={4} maxLength={750} showCount placeholder="Write a short bio about yourself..." />
                    </Form.Item>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '16px' }}>
                      <Switch checked={displayEmail} onChange={setDisplayEmail} />
                      <span style={{ fontSize: '14px', color: 'rgba(255,255,255,0.8)' }}>Display your account email</span>
                    </div>
                  </Form>
                </div>

                <div 
                  className="glass-card"
                  style={{ 
                    background: 'rgba(255,255,255,0.03)', 
                    backdropFilter: 'blur(20px)', 
                    WebkitBackdropFilter: 'blur(20px)',
                    border: '1px solid rgba(255,255,255,0.06)', 
                    borderRadius: '20px', 
                    padding: '32px',
                    boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
                    transition: 'all 0.2s ease',
                  }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                    <h2 className={playfair.className} style={{ fontSize: '18px', fontWeight: 600, margin: 0, color: '#F5F0E8' }}>Social Links</h2>
                    <a href="#custom" style={{ color: '#F5811F', fontSize: '13px', textDecoration: 'none' }}><PlusOutlined /> Add custom link</a>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div>
                      <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '6px' }}>Instagram</div>
                      <Input prefix={<InstagramOutlined />} placeholder="@username" />
                    </div>
                    <div>
                      <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '6px' }}>LinkedIn</div>
                      <Input prefix={<LinkedinOutlined />} placeholder="https://linkedin.com" />
                    </div>
                    <div>
                      <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '6px' }}>X (Twitter)</div>
                      <Input prefix={<TwitterOutlined />} placeholder="@username" />
                    </div>
                  </div>
                </div>
              </div>


              <div 
                className="glass-card"
                style={{ 
                  background: 'rgba(255,255,255,0.03)', 
                  backdropFilter: 'blur(20px)', 
                  WebkitBackdropFilter: 'blur(20px)',
                  border: '1px solid rgba(255,255,255,0.06)', 
                  borderRadius: '20px', 
                  padding: '32px', 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center', 
                  flexWrap: 'wrap', 
                  gap: '20px',
                  boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
                  transition: 'all 0.2s ease',
                }}>
                <div>
                  <h3 style={{ fontSize: '18px', fontWeight: 600, margin: 0, color: '#F5F0E8', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <SafetyOutlined style={{ color: '#F5811F', fontSize: '20px' }} /> Personalization Consent
                  </h3>
                  <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', margin: '4px 0 0 0' }}>Cho phép hệ thống sử dụng dữ liệu để gợi ý trải nghiệm cá nhân hóa.</p>
                </div>
                <Switch checked={consent} onChange={onConsentToggle} />
              </div>

              <div style={{ 
                background: 'rgba(26,26,26,0.4)', 
                backdropFilter: 'blur(16px)', 
                border: '1px solid rgba(255,255,255,0.05)', 
                borderRadius: '20px', 
                padding: '36px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.4), 0 1px 2px rgba(255,255,255,0.05) inset',
              }}>
                <h2 className={playfair.className} style={{ fontSize: '22px', fontWeight: 600, marginBottom: '12px', color: '#F5F0E8' }}>Featured badges</h2>
                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '14px', marginBottom: '16px' }}>Your first 3 claimed badges are featured automatically. Pick which ones show as icons next to your level.</p>
                <a href="#claim" style={{ color: '#F5811F', fontSize: '14px', textDecoration: 'underline' }}>Claim a badge to feature it here.</a>
              </div>

              <div style={{ 
                background: 'rgba(26,26,26,0.4)', 
                backdropFilter: 'blur(16px)', 
                border: '1px solid rgba(255,255,255,0.05)', 
                borderRadius: '20px', 
                padding: '48px 36px', 
                textAlign: 'center',
                boxShadow: '0 8px 32px rgba(0,0,0,0.4), 0 1px 2px rgba(255,255,255,0.05) inset',
              }}>
                <EnvironmentOutlined style={{ fontSize: '56px', color: 'rgba(255,255,255,0.15)', marginBottom: '20px' }} />
                <h3 className={playfair.className} style={{ fontSize: '24px', fontWeight: 600, color: '#F5F0E8', marginBottom: '12px' }}>No recent explorations yet</h3>
                <p style={{ color: 'rgba(255,255,255,0.5)', maxWidth: '480px', margin: '0 auto 24px auto', fontSize: '14px' }}>Start a conversation with the heritage chatbot to discover new cultural sites and save them to your journey.</p>
                <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap' }}>
                  <Button style={{ 
                    background: 'linear-gradient(135deg, #F5811F, #E85D04)', 
                    border: 'none', 
                    color: '#1A0A00', 
                    fontWeight: 700, 
                    borderRadius: '12px', 
                    height: '44px',
                    padding: '0 32px',
                    boxShadow: '0 4px 16px rgba(232,93,4,0.4)',
                  }}>Start Exploring</Button>
                  <Button style={{ 
                    background: 'rgba(26,26,26,0.6)', 
                    border: '1px solid rgba(255,255,255,0.2)', 
                    color: '#F5F0E8', 
                    borderRadius: '12px', 
                    height: '44px',
                    backdropFilter: 'blur(8px)',
                  }}>View My Journeys</Button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'milestones' && (
            <div>
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
                <div>
                  <h2 style={{ fontSize: '22px', fontWeight: 600, color: '#F5F0E8', margin: 0, marginBottom: '8px' }}>Exploration Levels</h2>
                  <p style={{ fontSize: '14px', color: 'rgba(255,255,255,0.5)', margin: 0 }}>
                    Reach 5 levels by discovering heritage, learning cultural stories, and exploring with your AI guide.
                  </p>
                </div>
                <a href="#" style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  🔗 Share progress
                </a>
              </div>

              {/* Level Cards Container */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                
                {/* Level 1 - Explorer (UNLOCKED) */}
                <div style={{ 
                  background: 'rgba(255, 255, 255, 0.03)', 
                  backdropFilter: 'blur(20px)', 
                  border: '1px solid rgba(255, 255, 255, 0.06)', 
                  borderRadius: '20px', 
                  padding: '32px',
                  boxShadow: '0 4px 24px rgba(0, 0, 0, 0.3)',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(245, 129, 31, 0.3)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)'}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'white', margin: 0, marginBottom: '4px' }}>Explorer</h3>
                      <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', margin: 0 }}>Begin your cultural heritage journey.</p>
                    </div>
                    <span style={{ fontSize: '13px', color: '#F5811F', whiteSpace: 'nowrap' }}>Explorer unlocked</span>
                  </div>
                  <div style={{ height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{ width: '100%', height: '100%', background: 'white' }} />
                  </div>
                </div>

                {/* Level 2 - Heritage Seeker (CURRENT - EXPANDED) */}
                <div style={{ 
                  background: 'rgba(255, 255, 255, 0.03)', 
                  backdropFilter: 'blur(20px)', 
                  border: '1px solid rgba(255, 255, 255, 0.06)', 
                  borderRadius: '20px', 
                  padding: '32px',
                  boxShadow: '0 4px 24px rgba(0, 0, 0, 0.3)',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(245, 129, 31, 0.3)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)'}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'white', margin: 0, marginBottom: '4px' }}>Heritage Seeker</h3>
                      <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', margin: 0 }}>Discover your first sites and learn the stories behind them.</p>
                    </div>
                    <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', whiteSpace: 'nowrap' }}>11 milestones to unlock this level</span>
                  </div>
                  
                  {/* 11 Milestones Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px 24px', marginTop: '16px' }}>
                    {['Explore your first heritage site', 'Discover 5 heritage sites', 'Read a site\'s history', 'Explore a heritage map', 'Ask the chatbot about a site', 'Learn about a local custom', 'Discover a traditional festival', 'Read 3 cultural stories', 'Share a heritage story', 'Complete your first journey', 'Ask 5 heritage questions'].map((milestone, idx) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', border: '1.5px solid rgba(255,255,255,0.3)', flexShrink: 0, marginTop: '2px' }} />
                        <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', lineHeight: '1.4' }}>{milestone}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Level 3 - Culture Scholar (LOCKED) */}
                <div style={{ 
                  background: 'rgba(255, 255, 255, 0.03)', 
                  backdropFilter: 'blur(20px)', 
                  border: '1px solid rgba(255, 255, 255, 0.06)', 
                  borderRadius: '20px', 
                  padding: '32px',
                  boxShadow: '0 4px 24px rgba(0, 0, 0, 0.3)',
                  transition: 'all 0.2s ease',
                  opacity: 0.6,
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(245, 129, 31, 0.3)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)'}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'white', margin: 0, marginBottom: '4px' }}>
                        🔒 Culture Scholar
                      </h3>
                      <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', margin: 0 }}>
                        Deepen your knowledge of history, architecture, and living traditions.
                      </p>
                    </div>
                    <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', whiteSpace: 'nowrap' }}>Unlock Heritage Seeker first</span>
                  </div>
                </div>

                {/* Level 4 - Journey Pathfinder (LOCKED) */}
                <div style={{ 
                  background: 'rgba(255, 255, 255, 0.03)', 
                  backdropFilter: 'blur(20px)', 
                  border: '1px solid rgba(255, 255, 255, 0.06)', 
                  borderRadius: '20px', 
                  padding: '32px',
                  boxShadow: '0 4px 24px rgba(0, 0, 0, 0.3)',
                  transition: 'all 0.2s ease',
                  opacity: 0.6,
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(245, 129, 31, 0.3)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)'}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'white', margin: 0, marginBottom: '4px' }}>
                        🔒 Journey Pathfinder
                      </h3>
                      <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', margin: 0 }}>
                        Connect heritage sites through meaningful cultural journeys.
                      </p>
                    </div>
                    <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', whiteSpace: 'nowrap' }}>Unlock Culture Scholar first</span>
                  </div>
                </div>

                {/* Level 5 - Heritage Ambassador (LOCKED) */}
                <div style={{ 
                  background: 'rgba(255, 255, 255, 0.03)', 
                  backdropFilter: 'blur(20px)', 
                  border: '1px solid rgba(255, 255, 255, 0.06)', 
                  borderRadius: '20px', 
                  padding: '32px',
                  boxShadow: '0 4px 24px rgba(0, 0, 0, 0.3)',
                  transition: 'all 0.2s ease',
                  opacity: 0.6,
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(245, 129, 31, 0.3)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)'}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'white', margin: 0, marginBottom: '4px' }}>
                        🔒 Heritage Ambassador
                      </h3>
                      <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', margin: 0 }}>
                        Explore for 7 days in a row and share the cultural stories you discover.
                      </p>
                    </div>
                    <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', whiteSpace: 'nowrap' }}>Unlock Journey Pathfinder first</span>
                  </div>
                </div>
              </div>

              {/* Footer Text */}
              <div style={{ textAlign: 'center', marginTop: '24px' }}>
                <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', margin: 0 }}>
                  Keep exploring, each milestone celebrates a new step in your heritage journey.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'achievements' && (
            <div style={{ 
              background: 'rgba(255, 255, 255, 0.03)', 
              backdropFilter: 'blur(20px)', 
              border: '1px solid rgba(255, 255, 255, 0.06)', 
              borderRadius: '20px', 
              padding: '48px 36px', 
              textAlign: 'center',
              boxShadow: '0 4px 24px rgba(0, 0, 0, 0.3)',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(245, 129, 31, 0.3)'}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)'}
            >
              <TrophyOutlined style={{ fontSize: '56px', color: '#F5811F', marginBottom: '20px' }} />
              <h2 className={playfair.className} style={{ fontSize: '26px', fontWeight: 600, color: '#F5F0E8', marginBottom: '12px' }}>Achievements & Badges</h2>
              <p style={{ color: 'rgba(255,255,255,0.5)' }}>Hoàn thành các cột mốc di sản để mở khóa huy hiệu danh giá.</p>
            </div>
          )}

        </div>

        {/* Responsive CSS */}
        <style dangerouslySetInnerHTML={{
          __html: `
            @media (max-width: 768px) {
              .profile-grid {
                grid-template-columns: 1fr !important;
              }
              .profile-header-row {
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 20px;
              }
              .profile-buttons {
                width: 100%;
                justify-content: stretch;
              }
              .profile-buttons button {
                flex: 1;
              }
            }
            @media (max-width: 640px) {
              .milestones-grid {
                grid-template-columns: repeat(2, 1fr) !important;
              }
            }
            .glass-card:hover {
              border-color: rgba(245, 129, 31, 0.3) !important;
            }
          `
        }} />
      </div>
    </ConfigProvider>
  );
}
