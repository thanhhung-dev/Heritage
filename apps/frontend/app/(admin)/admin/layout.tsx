'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ConfigProvider,
  Layout,
  Menu,
  Input,
  Button,
  Avatar,
  Space,
  Typography,
  Breadcrumb,
  App as AntApp,
} from 'antd';
import {
  DashboardOutlined,
  FileTextOutlined,
  EnvironmentOutlined,
  CalendarOutlined,
  GoldOutlined,
  InboxOutlined,
  ApartmentOutlined,
  AuditOutlined,
  BellOutlined,
  PlusOutlined,
  SearchOutlined,
  FolderOpenOutlined,
  DoubleLeftOutlined,
} from '@ant-design/icons';

import styles from './heritage.module.css';

// 1. HeritageLogo (Logo dải màu sọc đa sắc chuẩn Figma)
function HeritageLogo({ size = 32 }: { size?: number }) {
  const height = Math.round((size * 70) / 63);
  return (
    <svg
      width={size}
      height={height}
      viewBox="0 0 63 70"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0 }}
    >
      <g clipPath="url(#clip0_full)">
        <mask
          id="mask0_full"
          style={{ maskType: 'luminance' }}
          maskUnits="userSpaceOnUse"
          x="0"
          y="0"
          width="63"
          height="70"
        >
          <path
            d="M1.72887 25.8225C1.03346 23.8475 0.576935 21.5882 0.576935 19.3776C0.576935 17.1669 0.968 15.0395 1.66341 13.0793C1.68552 13.0373 1.68552 12.9953 1.70677 12.9541C4.48758 5.59129 11.8311 0.1689 19.9967 0.0642586H30.9194V38.7123H20.0052C11.7878 38.6077 4.44423 33.2685 1.72887 25.8225Z"
            fill="white"
          />
          <path d="M62.4035 0.0651002H20.8052V25.0554H62.4035V0.0651002Z" fill="white" />
          <path d="M25.1409 51.2083H0.57608V69.9045H25.1409V51.2083Z" fill="white" />
          <path d="M27.5153 14.1641L8.37482 34.6149L43.4786 67.4693L62.619 47.0185L27.5153 14.1641Z" fill="white" />
        </mask>
        <g mask="url(#mask0_full)">
          <path d="M63 0H0V14H63V0Z" fill="#FFAF01" />
          <path d="M63 14H0V28H63V14Z" fill="#FF8204" />
          <path d="M63 28H0V42H63V28Z" fill="#FA500F" />
          <path d="M63 42H0V56H63V42Z" fill="#E51300" />
          <path d="M63 56H0V70H63V56Z" fill="#C4001D" />
        </g>
      </g>
      <defs>
        <clipPath id="clip0_full">
          <rect width="63" height="70" fill="white" />
        </clipPath>
      </defs>
    </svg>
  );
}

// 2. HeritageLogoMini (dùng khi thu nhỏ sidebar)
function HeritageLogoMini({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 149 149" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="149" height="149" rx={8} fill="#FA500F" />
      <path d="M44 60C44 50 52 40 63 40H74V79H63C52 79 44 70 44 60Z" fill="white" />
      <rect x="64" y="40" width="41" height="25" fill="white" />
      <rect x="44" y="91" width="25" height="19" fill="white" />
      <rect x="51" y="75" width="28" height="48" transform="rotate(-47 51 75)" fill="white" />
    </svg>
  );
}

const { Header, Sider, Content } = Layout;

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  const menuItems = [
    {
      key: '/admin',
      icon: <DashboardOutlined />,
      label: <Link href="/admin">Overview</Link>,
    },
    {
      key: '/admin/documents',
      icon: <FileTextOutlined />,
      label: <Link href="/admin/documents">Knowledge Documents</Link>,
    },
    {
      key: 'structured',
      icon: <FolderOpenOutlined />,
      label: 'Structured Data',
      children: [
        {
          key: '/admin/places',
          icon: <EnvironmentOutlined />,
          label: <Link href="/admin/places">Places</Link>,
        },
        {
          key: '/admin/events',
          icon: <CalendarOutlined />,
          label: <Link href="/admin/events">Events</Link>,
        },
        {
          key: '/admin/artifacts',
          icon: <GoldOutlined />,
          label: <Link href="/admin/artifacts">Artifacts</Link>,
        },
      ],
    },
    {
      key: '/admin/review-queue',
      icon: <InboxOutlined />,
      label: <Link href="/admin/review-queue">Review Queue</Link>,
    },
    {
      key: '/admin/graph-evaluation',
      icon: <ApartmentOutlined />,
      label: <Link href="/admin/graph-evaluation">Graph & Evaluation</Link>,
    },
    {
      key: '/admin/audit-log',
      icon: <AuditOutlined />,
      label: <Link href="/admin/audit-log">Audit Log</Link>,
    },
  ];

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#ea580c',
          colorInfo: '#3a5a7a',
          colorSuccess: '#16a34a',
          colorWarning: '#b07d1a',
          colorError: '#c0492c',
          colorText: '#0f172a',
          colorTextSecondary: '#64748b',
          colorBorder: '#e2e8f0',
          colorBgLayout: '#f8fafc',
          borderRadius: 8,
          fontFamily: "'Poppins', sans-serif",
        },
        components: {
          Menu: {
            itemSelectedBg: '#fff7ed',
            itemSelectedColor: '#ea580c',
            itemBorderRadius: 8,
          },
          Button: {
            fontWeight: 600,
          },
        },
      }}
    >
      <AntApp>
        <Layout style={{ minHeight: '100vh', background: '#f8fafc', fontFamily: "'Poppins', sans-serif" }}>
          {/* Sidebar cố định 100vh */}
          <Sider
            width={264}
            collapsedWidth={76}
            collapsed={collapsed}
            trigger={null}
            theme="light"
            style={{
              height: '100vh',
              position: 'sticky',
              top: 0,
              left: 0,
              borderRight: '1px solid #eef2f6',
              background: '#ffffff',
              zIndex: 100,
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              {/* Header Sidebar có Logo chuẩn và nút toggle */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: collapsed ? 'center' : 'space-between',
                  padding: collapsed ? '16px 0' : '16px 18px',
                  borderBottom: '1px solid #f1f5f9',
                  minHeight: 70,
                  flexShrink: 0,
                }}
              >
                {collapsed ? (
                  <div onClick={() => setCollapsed(false)} style={{ cursor: 'pointer' }}>
                    <HeritageLogoMini size={32} />
                  </div>
                ) : (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <HeritageLogo size={32} />
                      <div>
                        <div
                          style={{
                            fontWeight: 700,
                            fontSize: 16,
                            color: '#0f172a',
                            lineHeight: 1.2,
                            letterSpacing: '-0.02em',
                          }}
                        >
                          Heritage
                        </div>
                        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 1 }}>
                          Knowledge Administr...
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => setCollapsed(!collapsed)}
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: 6,
                        border: '1px solid #e2e8f0',
                        background: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        color: '#94a3b8',
                        outline: 'none',
                      }}
                    >
                      <DoubleLeftOutlined style={{ fontSize: 11 }} />
                    </button>
                  </>
                )}
              </div>

              {/* Menu cuộn */}
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <Menu
                  mode="inline"
                  selectedKeys={[pathname]}
                  defaultOpenKeys={['structured']}
                  items={menuItems}
                  className={styles['main-menu']}
                  style={{ fontFamily: "'Poppins', sans-serif", borderRight: 0 }}
                />
              </div>

              {/* KHỐI ACCOUNT BẮT BUỘC DÍNH CHẶT DƯỚI GÓC ĐÁY MÀN HÌNH */}
              <div
                style={{
                  padding: '16px',
                  borderTop: '1px solid #f1f5f9',
                  background: '#ffffff',
                  marginTop: 'auto',
                  flexShrink: 0,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 10px',
                    borderRadius: 10,
                    border: '1px solid #e2e8f0',
                  }}
                >
                  <Avatar style={{ backgroundColor: '#ffedd5', color: '#ea580c', fontWeight: 600, flexShrink: 0 }}>
                    VQ
                  </Avatar>
                  {!collapsed && (
                    <div style={{ minWidth: 0, overflow: 'hidden' }}>
                      <div
                        style={{
                          fontWeight: 600,
                          fontSize: 13,
                          color: '#0f172a',
                          whiteSpace: 'nowrap',
                          textOverflow: 'ellipsis',
                          overflow: 'hidden',
                        }}
                      >
                        Dang Quoc Viet
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          color: '#94a3b8',
                          whiteSpace: 'nowrap',
                          textOverflow: 'ellipsis',
                          overflow: 'hidden',
                        }}
                      >
                        Knowledge Admin...
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </Sider>

          {/* Nội dung bên phải */}
          <Layout style={{ minWidth: 0 }}>
            <Header className={styles['app-header']}>
              <div className={styles['page-heading']}>
                <Breadcrumb
                  items={[
                    { title: 'HeritageGraph' },
                    { title: 'Overview' },
                  ]}
                  style={{ fontFamily: "'Poppins', sans-serif" }}
                />
                <Typography.Title level={3} style={{ margin: 0, fontFamily: "'Poppins', sans-serif" }}>
                  Knowledge Base Overview
                </Typography.Title>
              </div>

              <Space size={12}>
                <Input
                  className={styles['global-search']}
                  prefix={<SearchOutlined style={{ color: '#94a3b8' }} />}
                  placeholder="Search everywhere…"
                  style={{ fontFamily: "'Poppins', sans-serif" }}
                />
                <Button aria-label="Notifications" icon={<BellOutlined />} />
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  style={{ backgroundColor: '#ea580c', borderColor: '#ea580c', color: '#fff', fontFamily: "'Poppins', sans-serif" }}
                >
                  Add Document
                </Button>
              </Space>
            </Header>

            <Content className={styles['app-content']} style={{ fontFamily: "'Poppins', sans-serif" }}>
              {children}
            </Content>
          </Layout>
        </Layout>
      </AntApp>
    </ConfigProvider>
  );
}