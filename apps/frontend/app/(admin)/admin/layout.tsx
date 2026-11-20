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
  theme as antdTheme,
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
import { tapestryColors } from '@/styles/theme/heritageTheme';
import FontLoader from '@/components/FontLoader';
import { DesignIcon, KnowledgeBrand } from '@/features/knowledge/DesignIcon';
import { KnowledgeAccount } from '@/features/knowledge/KnowledgeAccount';
import knowledgeStyles from '@/features/knowledge/knowledge.module.css';

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
  const libraryMode = pathname.startsWith('/admin/documents');
  const adminFont = libraryMode ? 'Roboto, Arial, sans-serif' : "'Poppins', sans-serif";
  const adminColors = libraryMode ? { ...tapestryColors, primary: '#201f1c', background: '#fbfbf8',
    surface: '#f8f7f3', surfaceHover: '#ebe9e0', border: 'rgba(0,0,0,.1)', borderStrong: 'rgba(0,0,0,.15)' } : tapestryColors;
  const libraryMenu = [
    { key: '/admin', icon: <DesignIcon name="library-DashboardIcon" />, label: <Link href="/admin">Dashboard</Link> },
    { key: '/admin/documents', icon: <DesignIcon name="library-Files" />, label: <Link href="/admin/documents">Document library</Link> },
    { key: '/admin/documents/review', icon: <DesignIcon name="library-ClipboardCheck" />, label: <Link href="/admin/documents/review">Pending review</Link> },
    { key: '/admin/documents/ingestion', icon: <DesignIcon name="library-Hash" />, label: <Link href="/admin/documents/ingestion">Ingestion</Link> },
    { type: 'group' as const, label: 'ADMINISTRATION', children: [
      { key: 'library-members', disabled: true, icon: <DesignIcon name="library-Users" />, label: 'Members' },
      { key: 'library-activity', disabled: true, icon: <DesignIcon name="library-Eye" />, label: 'Activity log' },
    ] },
  ];
  const librarySelection = pathname.startsWith('/admin/documents/review') ? '/admin/documents/review'
    : pathname.startsWith('/admin/documents/ingestion') ? '/admin/documents/ingestion' : '/admin/documents';

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
        ...(libraryMode ? { inherit: false, algorithm: antdTheme.defaultAlgorithm } : {}),
        token: {
          colorPrimary: adminColors.primary,
          colorInfo: adminColors.primary,
          colorSuccess: '#16a34a',
          colorWarning: '#b07d1a',
          colorError: '#c0492c',
          colorText: libraryMode ? '#201f1c' : 'rgba(240, 232, 221, 0.85)',
          colorTextSecondary: libraryMode ? '#928f86' : 'rgba(240, 232, 221, 0.5)',
          colorBorder: adminColors.border,
          colorBgLayout: adminColors.background,
          borderRadius: libraryMode ? 12 : 8,
          ...(libraryMode ? { controlHeight: 32, colorBgContainer: '#fff',
            colorTextDisabled: '#928f86', colorBgContainerDisabled: '#f8f7f3' } : {}),
          fontFamily: adminFont,
        },
        components: {
          Menu: {
            itemSelectedBg: libraryMode ? 'rgba(0,0,0,.06)' : 'rgba(255, 155, 45, 0.15)',
            itemSelectedColor: adminColors.primary,
            itemBorderRadius: 8,
            ...(libraryMode ? { itemHeight: 32, itemMarginBlock: 2, itemMarginInline: 4,
              itemColor: '#201f1c', itemDisabledColor: '#928f86', groupTitleColor: '#928f86' } : {}),
          },
          Button: {
            fontWeight: libraryMode ? 400 : 600,
          },
          ...(libraryMode ? {
            Modal: { contentBg: '#fff', headerBg: '#fff', titleColor: '#201f1c', borderRadiusLG: 14 },
            Tree: { nodeSelectedBg: 'rgba(0,0,0,.06)', nodeSelectedColor: '#201f1c' },
          } : {}),
        },
      }}
    >
      <AntApp>
        {libraryMode && <FontLoader url="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;600&display=swap" />}
        <Layout className={libraryMode ? knowledgeStyles.chrome : undefined} style={{ minHeight: '100vh', background: adminColors.background, fontFamily: adminFont }}>
          {/* Sidebar cố định 100vh */}
          <Sider
            width={libraryMode ? 260 : 264}
            collapsedWidth={libraryMode ? 64 : 76}
            breakpoint={libraryMode ? 'lg' : undefined}
            onBreakpoint={broken => { if (libraryMode) setCollapsed(broken); }}
            collapsed={collapsed}
            trigger={null}
            theme={libraryMode ? 'light' : 'dark'}
            style={{
              height: '100vh',
              position: 'sticky',
              top: 0,
              left: 0,
              borderRight: `1px solid ${adminColors.border}`,
              background: adminColors.surface,
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
                  borderBottom: libraryMode ? 'none' : `1px solid ${tapestryColors.border}`,
                  minHeight: libraryMode ? 52 : 70,
                  flexShrink: 0,
                }}
              >
                {libraryMode ? <>
                  {!collapsed && <Link href="/admin" aria-label="Heritage Admin"><KnowledgeBrand /></Link>}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    {!collapsed && <Link href="/admin/documents?focus=search" aria-label="Search documents" className={knowledgeStyles.chromeToggle}><DesignIcon name="library-SearchIcon" /></Link>}
                    <button type="button" className={knowledgeStyles.chromeToggle} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={() => setCollapsed(!collapsed)}><DesignIcon name="library-CollapseSidebar" /></button>
                  </div>
                </> : collapsed ? (
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
                            color: 'rgba(240, 232, 221, 0.85)',
                            lineHeight: 1.2,
                            letterSpacing: '-0.02em',
                          }}
                        >
                          Heritage
                        </div>
                        <div style={{ fontSize: 11, color: 'rgba(240, 232, 221, 0.3)', marginTop: 1 }}>
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
                        border: `1px solid ${tapestryColors.borderStrong}`,
                        background: tapestryColors.surfaceHover,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        color: 'rgba(240, 232, 221, 0.5)',
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
                {libraryMode && !collapsed && <div className={knowledgeStyles.navLabel}>HERITAGE ADMIN</div>}
                <Menu
                  mode="inline"
                  selectedKeys={[libraryMode ? librarySelection : pathname]}
                  defaultOpenKeys={['structured']}
                  items={libraryMode ? libraryMenu : menuItems}
                  className={libraryMode ? knowledgeStyles.mainMenu : styles['main-menu']}
                  style={{ fontFamily: adminFont, borderRight: 0, background: libraryMode ? 'transparent' : undefined }}
                />
              </div>

              {/* KHỐI ACCOUNT BẮT BUỘC DÍNH CHẶT DƯỚI GÓC ĐÁY MÀN HÌNH */}
              {libraryMode ? <KnowledgeAccount collapsed={collapsed} /> : <div
                style={{
                  padding: '16px',
                  borderTop: `1px solid ${tapestryColors.border}`,
                  background: tapestryColors.surface,
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
                    border: `1px solid ${tapestryColors.border}`,
                  }}
                >
                  <Avatar style={{ backgroundColor: 'rgba(255, 155, 45, 0.15)', color: tapestryColors.primary, fontWeight: 600, flexShrink: 0 }}>
                    VQ
                  </Avatar>
                  {!collapsed && (
                    <div style={{ minWidth: 0, overflow: 'hidden' }}>
                      <div
                        style={{
                          fontWeight: 600,
                          fontSize: 13,
                          color: 'rgba(240, 232, 221, 0.85)',
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
                          color: 'rgba(240, 232, 221, 0.3)',
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
              </div>}
            </div>
          </Sider>

          {/* Nội dung bên phải */}
          <Layout style={{ minWidth: 0 }}>
            {!libraryMode && <Header className={styles['app-header']}>
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
                  prefix={<SearchOutlined style={{ color: 'rgba(240, 232, 221, 0.5)' }} />}
                  placeholder="Search everywhere..."
                  style={{ fontFamily: "'Poppins', sans-serif" }}
                />
                <Button aria-label="Notifications" icon={<BellOutlined />} />
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  style={{ backgroundColor: tapestryColors.primary, borderColor: tapestryColors.primary, color: '#0a0e14', fontFamily: "'Poppins', sans-serif" }}
                >
                  Add Document
                </Button>
              </Space>
            </Header>}

            <Content className={libraryMode ? knowledgeStyles.content : styles['app-content']} style={{ fontFamily: adminFont }}>
              {children}
            </Content>
          </Layout>
        </Layout>
      </AntApp>
    </ConfigProvider>
  );
}
