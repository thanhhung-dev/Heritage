'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { ConfigProvider, App as AntApp } from 'antd';
import { adminToken, clearAdminSession, signOutAdmin, verifyAdmin } from '@/features/admin-auth/admin-session';
import { resetDocuments } from '@/features/admin-documents/mock-documents';
import {
  DashboardOutlined,
  FileTextOutlined,
  AuditOutlined,
  NumberOutlined,
  TeamOutlined,
  EyeOutlined,
  ArrowLeftOutlined,
  UserOutlined,
  SearchOutlined,
  LayoutOutlined,
} from '@ant-design/icons';

function HeritageLogo({ size = 24 }: { size?: number }) {
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

const ADMIN_NAV = [
  { key: '/admin', label: 'Dashboard', icon: <DashboardOutlined /> },
  { key: '/admin/documents', label: 'Document library', icon: <FileTextOutlined /> },
  { key: '/admin/review-queue', label: 'Pending review', icon: <AuditOutlined /> },
  { key: '/admin/ingestion', label: 'Ingestion', icon: <NumberOutlined /> },
];

const ADMINISTRATION_NAV = [
  { key: '/admin/members', label: 'Members', icon: <TeamOutlined /> },
  { key: '/admin/audit-log', label: 'Activity log', icon: <EyeOutlined /> },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const [access, setAccess] = useState<{ path: string; state: 'checking' | 'allowed' | 'unavailable' | 'forbidden' }>({ path: '', state: 'checking' });

  useEffect(() => {
    if (pathname === '/admin/login') { setAccess({ path: '', state: 'checking' }); return; }
    let controller: AbortController | undefined;
    function revalidate() {
      controller?.abort();
      const current = new AbortController();
      controller = current;
      setAccess({ path: pathname, state: 'checking' });
      const token = adminToken();
      if (!token) { router.replace('/admin/login'); return; }
      void verifyAdmin(token, current.signal).then(result => {
        if (current.signal.aborted) return;
        if (result === 'unauthorized') { clearAdminSession(); router.replace('/admin/login'); }
        else setAccess({ path: pathname, state: result });
      });
    }
    function onVisibilityChange() {
      if (document.visibilityState === 'visible') revalidate();
    }
    revalidate();
    window.addEventListener('storage', revalidate);
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      controller?.abort();
      window.removeEventListener('storage', revalidate);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [pathname, router]);

  async function handleSignOut() {
    const confirmed = await signOutAdmin();
    resetDocuments();
    router.replace(confirmed ? '/admin/login' : '/admin/login?logout=unconfirmed');
  }

  if (pathname === '/admin/login') return <>{children}</>;

  if (access.path !== pathname || access.state !== 'allowed') {
    return <main role="status" style={{ padding: 32, color: 'var(--auth-text)', background: 'var(--auth-panel)', minHeight: '100vh' }}>
      {access.path === pathname && access.state === 'forbidden' ? 'This account does not have administrator access.' : access.path === pathname && access.state === 'unavailable' ? 'Unable to verify your session. Please try again.' : 'Checking admin session…'}
      {access.path === pathname && (access.state === 'forbidden' || access.state === 'unavailable') && <p><Link href="/admin/login">Back to admin sign in</Link></p>}
    </main>;
  }

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#FA500F',
          borderRadius: 8,
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        },
      }}
    >
      <AntApp>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
        />
        <div
          style={{
            display: 'flex',
            minHeight: '100vh',
            backgroundColor: '#F8F7F3',
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
            color: '#111827',
          }}
        >
          {/* Sidebar sáng BoardUI / Figma (#F8F7F3) */}
         <aside
            style={{
              width: collapsed ? 68 : 260,
              flexShrink: 0,
              backgroundColor: '#F8F7F3',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              transition: 'width 0.2s ease',
              userSelect: 'none',
            }}
          >
            {/* App switcher / Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: collapsed ? 'center' : 'space-between',
                padding: collapsed ? '18px 0' : '18px 16px 14px 18px',
              }}
            >
              <Link
                href="/admin"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  textDecoration: 'none',
                }}
              >
                <HeritageLogo size={23} />
                {!collapsed && (
                  <span
                    style={{
                      fontWeight: 800,
                      fontSize: 16,
                      letterSpacing: '0.03em',
                      color: '#000000',
                    }}
                  >
                    HERITAGE
                  </span>
                )}
              </Link>

              {!collapsed && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#6B7280' }}>
                  <button
                    type="button"
                    aria-label="Search"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      padding: 4,
                      cursor: 'pointer',
                      color: '#6B7280',
                      display: 'flex',
                      alignItems: 'center',
                    }}
                  >
                    <SearchOutlined style={{ fontSize: 14 }} />
                  </button>
                  <button
                    type="button"
                    aria-label="Toggle sidebar"
                    onClick={() => setCollapsed(true)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      padding: 4,
                      cursor: 'pointer',
                      color: '#6B7280',
                      display: 'flex',
                      alignItems: 'center',
                    }}
                  >
                    <LayoutOutlined style={{ fontSize: 14 }} />
                  </button>
                </div>
              )}
            </div>

            {collapsed && (
              <button
                type="button"
                aria-label="Expand sidebar"
                onClick={() => setCollapsed(false)}
                style={{
                  margin: '0 auto 8px',
                  background: 'transparent',
                  border: 'none',
                  padding: 6,
                  cursor: 'pointer',
                  color: '#6B7280',
                }}
              >
                <LayoutOutlined style={{ fontSize: 15 }} />
              </button>
            )}

            {/* Navigation */}
            <nav style={{ flex: 1, overflowY: 'auto', padding: '8px 14px' }}>
              {!collapsed && (
                <div
                  style={{
                    fontSize: 10.5,
                    fontWeight: 500,
                    color: '#9CA3AF',
                    letterSpacing: '0.04em',
                    padding: '6px 8px 6px',
                  }}
                >
                  HERITAGE ADMIN
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {ADMIN_NAV.map((item) => {
                  const active = pathname === item.key;
                  return (
                    <Link
                      key={item.key}
                      href={item.key}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: collapsed ? 'center' : 'flex-start',
                        gap: 10,
                        padding: '8px 10px',
                        borderRadius: 8,
                        fontSize: 13,
                        fontWeight: active ? 500 : 400,
                        color: active ? '#111827' : '#374151',
                        backgroundColor: active ? '#ECEAE4' : 'transparent',
                        textDecoration: 'none',
                        transition: 'background-color 0.15s ease',
                      }}
                    >
                      <span style={{ fontSize: 14, color: active ? '#111827' : '#4B5563', display: 'flex' }}>
                        {item.icon}
                      </span>
                      {!collapsed && <span>{item.label}</span>}
                    </Link>
                  );
                })}
              </div>

              {!collapsed && (
                <div
                  style={{
                    fontSize: 10.5,
                    fontWeight: 500,
                    color: '#9CA3AF',
                    letterSpacing: '0.04em',
                    padding: '18px 8px 6px',
                  }}
                >
                  ADMINISTRATION
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: collapsed ? 16 : 0 }}>
                {ADMINISTRATION_NAV.map((item) => {
                  const active = pathname === item.key;
                  return (
                    <Link
                      key={item.key}
                      href={item.key}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: collapsed ? 'center' : 'flex-start',
                        gap: 10,
                        padding: '8px 10px',
                        borderRadius: 8,
                        fontSize: 13,
                        fontWeight: active ? 500 : 400,
                        color: active ? '#111827' : '#374151',
                        backgroundColor: active ? '#ECEAE4' : 'transparent',
                        textDecoration: 'none',
                        transition: 'background-color 0.15s ease',
                      }}
                    >
                      <span style={{ fontSize: 14, color: active ? '#111827' : '#4B5563', display: 'flex' }}>
                        {item.icon}
                      </span>
                      {!collapsed && <span>{item.label}</span>}
                    </Link>
                  );
                })}
              </div>
            </nav>

            {/* Support & Account ở đáy */}
            <div style={{ padding: '12px 14px 18px' }}>
              {!collapsed && (
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 500,
                    color: '#9CA3AF',
                    padding: '0 8px 6px',
                  }}
                >
                  Support
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginBottom: 10 }}>
                <Link
                  href="/"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    gap: 10,
                    padding: '7px 10px',
                    borderRadius: 8,
                    fontSize: 13,
                    fontWeight: 400,
                    color: '#374151',
                    textDecoration: 'none',
                  }}
                >
                  <ArrowLeftOutlined style={{ fontSize: 13, color: '#4B5563' }} />
                  {!collapsed && <span>Back to Chat</span>}
                </Link>
                <button
                  type="button"
                  onClick={handleSignOut}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    gap: 10,
                    padding: '7px 10px',
                    borderRadius: 8,
                    fontSize: 13,
                    fontWeight: 400,
                    color: '#374151',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontFamily: 'inherit',
                  }}
                >
                  <UserOutlined style={{ fontSize: 13, color: '#4B5563' }} />
                  {!collapsed && <span>Account / Sign out</span>}
                </button>
              </div>

              <div
                style={{
                  paddingTop: 10,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: collapsed ? 'center' : 'space-between',
                  paddingLeft: collapsed ? 0 : 8,
                  paddingRight: collapsed ? 0 : 8,
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                      backgroundColor: '#EAE8E1',
                      color: '#4B5563',
                      fontSize: 12,
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    HT
                  </div>
                  {!collapsed && (
                    <div style={{ minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 500,
                          color: '#111827',
                          lineHeight: 1.25,
                        }}
                      >
                        Hung
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          fontWeight: 400,
                          color: '#9CA3AF',
                          lineHeight: 1.25,
                        }}
                      >
                        Default Workspace
                      </div>
                    </div>
                  )}
                </div>

                {!collapsed && (
                  <span style={{ fontSize: 12, color: '#6B7280' }}>⌄</span>
                )}
              </div>
            </div>
          </aside>

          {/* Workspace Surround */}
          <main
            style={{
              flex: 1,
              minWidth: 0,
              padding: '10px 10px 10px 0',
              display: 'flex',
            }}
          >
            <div
              style={{
                flex: 1,
                minWidth: 0,
                backgroundColor: '#FFFFFF',
                borderRadius: 12,
                border: '1px solid #EBE9E2',
                overflow: 'hidden',
              }}
            >
              {children}
            </div>
          </main>
        </div>
      </AntApp>
    </ConfigProvider>
  );
}
