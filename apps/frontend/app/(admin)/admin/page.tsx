'use client';

import React from 'react';
import { Row, Col, Card, Button, Typography, Tag, Space } from 'antd';
import {
  FileTextOutlined,
  ApartmentOutlined,
  BranchesOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  ReloadOutlined,
  PlusOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  RightOutlined,
} from '@ant-design/icons';
import styles from './heritage.module.css';

const { Title, Text } = Typography;

export default function OverviewPage() {
  const categoryStats = [
    { name: 'Monuments & Architecture', value: 432, width: '92%' },
    { name: 'Festivals & Beliefs', value: 380, width: '78%' },
    { name: 'Cuisine', value: 295, width: '62%' },
    { name: 'Traditional Crafts', value: 240, width: '51%' },
    { name: 'Performing Arts', value: 215, width: '45%' },
    { name: 'Historical Figures', value: 168, width: '35%' },
  ];

  const evaluations = [
    { label: 'Recall@7', actual: 86, target: 85 },
    { label: 'Entity Micro-F1', actual: 92, target: 88 },
    { label: 'Citation Accuracy', actual: 96, target: 94 },
    { label: 'Retrieval Accuracy', actual: 88, target: 86 },
    { label: 'Intent Macro-F1', actual: 82, target: 82 },
    { label: 'Recommendation P@5', actual: 80, target: 80 },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Top Banner */}
      <div className={styles['split-row']}>
        <div>
          <Title level={4} style={{ margin: 0 }}>
            Knowledge Base Overview
          </Title>
          <Text type="secondary" style={{ fontSize: 13 }}>
            Version <strong style={{ color: '#334155' }}>corpus v14</strong> · Last graph build at <strong style={{ color: '#0f172a' }}>2025-09-24 09:47</strong>
          </Text>
        </div>

        <Space>
          <Button icon={<ReloadOutlined />}>Rebuild Graph</Button>
          <Button type="primary" icon={<PlusOutlined />} style={{ backgroundColor: '#ea580c', borderColor: '#ea580c' }}>
            Add Document
          </Button>
        </Space>
      </div>

      {/* 5 KPI Stat Cards */}
      <Row gutter={[14, 14]}>
        <Col xs={24} sm={12} md={true} style={{ flex: 1, minWidth: 190 }}>
          <Card bordered className={styles['kpi-card']}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: 12 }}>
              <span>Total Documents</span>
              <FileTextOutlined style={{ color: '#cbd5e1' }} />
            </div>
            <h2>1,284</h2>
            <div className={styles['status-danger']}>
              <ArrowUpOutlined /> +46 vs. previous version
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={true} style={{ flex: 1, minWidth: 190 }}>
          <Card bordered className={styles['kpi-card']}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: 12 }}>
              <span>Total Entities</span>
              <ApartmentOutlined style={{ color: '#cbd5e1' }} />
            </div>
            <h2>9,317</h2>
            <div className={styles['status-success']}>
              <ArrowUpOutlined /> +317 vs. previous version
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={true} style={{ flex: 1, minWidth: 190 }}>
          <Card bordered className={styles['kpi-card']}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: 12 }}>
              <span>Total Relations</span>
              <BranchesOutlined style={{ color: '#cbd5e1' }} />
            </div>
            <h2>21,640</h2>
            <div className={styles['status-success']}>
              <ArrowUpOutlined /> +884 vs. previous version
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={true} style={{ flex: 1, minWidth: 190 }}>
          <Card bordered className={styles['kpi-card']}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: 12 }}>
              <span>Records Pending Review</span>
              <ClockCircleOutlined style={{ color: '#cbd5e1' }} />
            </div>
            <h2>73</h2>
            <div style={{ fontSize: 12, color: '#64748b' }}>
              <ArrowDownOutlined /> -12 vs. previous version
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={true} style={{ flex: 1, minWidth: 190 }}>
          <Card bordered className={`${styles['kpi-card']} ${styles['kpi-card-warning']}`}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#c0492c', fontSize: 12, fontWeight: 600 }}>
              <span>Fields Missing Sources</span>
              <WarningOutlined style={{ color: '#c0492c' }} />
            </div>
            <h2 style={{ color: '#c0492c' }}>128</h2>
            <div className={styles['status-danger']}>
              <ArrowUpOutlined /> +19 vs. previous version
            </div>
          </Card>
        </Col>
      </Row>

      {/* Row 1: Documents by Category & Source Completeness */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={15}>
          <Card title="Documents by Category" bordered style={{ borderRadius: 12, height: '100%' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {categoryStats.map((item) => (
                <div key={item.name} style={{ display: 'flex', alignItems: 'center', fontSize: 12 }}>
                  <div style={{ width: 170, color: '#64748b', textAlign: 'right', paddingRight: 16 }}>
                    {item.name}
                  </div>
                  <div style={{ flex: 1, backgroundColor: '#f1f5f9', height: 14, borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ width: item.width, backgroundColor: '#ea580c', height: '100%', borderRadius: 4 }} />
                  </div>
                  <div style={{ width: 45, textAlign: 'right', fontWeight: 600, color: '#0f172a', paddingLeft: 8 }}>
                    {item.value}
                  </div>
                </div>
              ))}
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingLeft: 170, paddingRight: 45, fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                <span>0</span>
                <span>90</span>
                <span>180</span>
                <span>270</span>
                <span>360</span>
              </div>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={9}>
          <Card title="Source Completeness" bordered style={{ borderRadius: 12, height: '100%' }}>
            <div className={styles['source-donut']}>
              <div className={styles['source-donut-chart']}>
                <svg viewBox="0 0 42 42" style={{ width: 130, height: 130, transform: 'rotate(-90deg)', display: 'block', margin: '0 auto' }}>
                  <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#f1f5f9" strokeWidth="6" />
                  <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#ea580c" strokeWidth="6" strokeDasharray="69 31" strokeDashoffset="0" />
                  <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#d97706" strokeWidth="6" strokeDasharray="17 83" strokeDashoffset="-69" />
                  <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#9a3412" strokeWidth="6" strokeDasharray="10 90" strokeDashoffset="-86" />
                  <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#94a3b8" strokeWidth="6" strokeDasharray="4 96" strokeDashoffset="-96" />
                </svg>
              </div>

              <div className={styles['chart-legend']}>
                <div className={styles['chart-legend-row']}>
                  <span className={styles['chart-legend-label']}><span className={styles['chart-legend-swatch']} style={{ backgroundColor: '#ea580c' }} /> Sources Complete</span>
                  <strong>69%</strong>
                </div>
                <div className={styles['chart-legend-row']}>
                  <span className={styles['chart-legend-label']}><span className={styles['chart-legend-swatch']} style={{ backgroundColor: '#d97706' }} /> Missing URL</span>
                  <strong>17%</strong>
                </div>
                <div className={styles['chart-legend-row']}>
                  <span className={styles['chart-legend-label']}><span className={styles['chart-legend-swatch']} style={{ backgroundColor: '#9a3412' }} /> Missing Quote</span>
                  <strong>10%</strong>
                </div>
                <div className={styles['chart-legend-row']}>
                  <span className={styles['chart-legend-label']}><span className={styles['chart-legend-swatch']} style={{ backgroundColor: '#94a3b8' }} /> Not Reviewed</span>
                  <strong>4%</strong>
                </div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Row 2: Review Status by Type & Graph Size by Version */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Review Status by Type" bordered style={{ borderRadius: 12 }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', height: 180, borderBottom: '1px solid #f1f5f9', paddingBottom: 10 }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 48 }}>
                <div style={{ width: 34, height: 14, backgroundColor: '#991b1b', borderRadius: '3px 3px 0 0' }} />
                <div style={{ width: 34, height: 20, backgroundColor: '#78716c' }} />
                <div style={{ width: 34, height: 105, backgroundColor: '#ea580c' }} />
                <span style={{ fontSize: 11, color: '#64748b', marginTop: 8 }}>Document</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 48 }}>
                <div style={{ width: 34, height: 8, backgroundColor: '#78716c', borderRadius: '3px 3px 0 0' }} />
                <div style={{ width: 34, height: 45, backgroundColor: '#ea580c' }} />
                <span style={{ fontSize: 11, color: '#64748b', marginTop: 8 }}>Place</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 48 }}>
                <div style={{ width: 34, height: 28, backgroundColor: '#ea580c', borderRadius: '3px 3px 0 0' }} />
                <span style={{ fontSize: 11, color: '#64748b', marginTop: 8 }}>Event</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 48 }}>
                <div style={{ width: 34, height: 36, backgroundColor: '#ea580c', borderRadius: '3px 3px 0 0' }} />
                <span style={{ fontSize: 11, color: '#64748b', marginTop: 8 }}>Artifact</span>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 12, fontSize: 11, color: '#64748b' }}>
              <span><span style={{ display: 'inline-block', width: 8, height: 8, backgroundColor: '#cbd5e1', marginRight: 4 }} />Draft</span>
              <span><span style={{ display: 'inline-block', width: 8, height: 8, backgroundColor: '#78716c', marginRight: 4 }} />In Review</span>
              <span><span style={{ display: 'inline-block', width: 8, height: 8, backgroundColor: '#ea580c', marginRight: 4 }} />Published</span>
              <span><span style={{ display: 'inline-block', width: 8, height: 8, backgroundColor: '#991b1b', marginRight: 4 }} />Rejected</span>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Graph Size by Version" bordered style={{ borderRadius: 12 }}>
            <div style={{ height: 180, display: 'flex', flexDirection: 'column', justifyContent: 'center', borderBottom: '1px solid #f1f5f9' }}>
              <svg viewBox="0 0 400 150" style={{ width: '100%', height: '100%' }}>
                <polyline fill="none" stroke="#ea580c" strokeWidth="2.5" points="10,130 90,115 170,95 250,75 330,55 390,40" />
                <polyline fill="none" stroke="#f59e0b" strokeWidth="2" points="10,135 90,125 170,115 250,105 330,95 390,88" />
                <polyline fill="none" stroke="#64748b" strokeWidth="1.5" points="10,145 90,144 170,143 250,142 330,141 390,140" />
              </svg>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94a3b8', marginTop: 8 }}>
              <span>v9</span>
              <span>v10</span>
              <span>v11</span>
              <span>v12</span>
              <span>v13</span>
              <span>v14</span>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Row 3: Latest Evaluation Results */}
      <Card
        title="Latest Evaluation Results"
        extra={<span style={{ fontSize: 12, color: '#94a3b8' }}>Compared with target</span>}
        bordered
        style={{ borderRadius: 12 }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'flex-end', height: 160, borderBottom: '1px solid #f1f5f9', paddingBottom: 10 }}>
          {evaluations.map((item) => (
            <div key={item.label} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 85 }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                <div style={{ width: 22, height: item.actual, backgroundColor: '#ea580c', borderRadius: '2px 2px 0 0' }} />
                <div style={{ width: 22, height: item.target, backgroundColor: '#e2e8f0', borderRadius: '2px 2px 0 0' }} />
              </div>
              <span style={{ fontSize: 11, color: '#64748b', marginTop: 8, textAlign: 'center' }}>
                {item.label}
              </span>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginTop: 12, fontSize: 11, color: '#64748b' }}>
          <span><span style={{ display: 'inline-block', width: 10, height: 10, backgroundColor: '#ea580c', marginRight: 6 }} />Actual</span>
          <span><span style={{ display: 'inline-block', width: 10, height: 10, backgroundColor: '#e2e8f0', marginRight: 6 }} />Target</span>
        </div>
      </Card>

      {/* Row 4: Needs Attention & Recent Activity */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card
            title="Needs Attention"
            extra={<Button type="link" size="small" style={{ color: '#ea580c' }}>View All <RightOutlined /></Button>}
            bordered
            style={{ borderRadius: 12 }}
          >
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div className={styles['attention-item']}>
                <div className={`${styles['list-icon']} ${styles['danger']}`}>
                  <WarningOutlined />
                </div>
                <div className={styles['attention-copy']}>
                  <strong style={{ fontSize: 13 }}>Thanh Khe Whale Worship Festival</strong>
                  <Text type="secondary" style={{ fontSize: 11 }}>DOC-1128 · Document · Missing source URL</Text>
                </div>
                <Tag color="error">Missing Sources</Tag>
              </div>

              <div className={styles['attention-item']}>
                <div className={`${styles['list-icon']} ${styles['danger']}`}>
                  <WarningOutlined />
                </div>
                <div className={styles['attention-copy']}>
                  <strong style={{ fontSize: 13 }}>Tara Bodhisattva Statue</strong>
                  <Text type="secondary" style={{ fontSize: 11 }}>ART-419 · Artifact · Missing source URL for period</Text>
                </div>
                <Tag color="error">Missing Sources</Tag>
              </div>

              <div className={styles['attention-item']}>
                <div className={`${styles['list-icon']} ${styles['danger']}`}>
                  <WarningOutlined />
                </div>
                <div className={styles['attention-copy']}>
                  <strong style={{ fontSize: 13 }}>Tu Duc Tomb</strong>
                  <Text type="secondary" style={{ fontSize: 11 }}>PLE-214 · Place · Missing supporting quote for coordinates</Text>
                </div>
                <Tag color="error">Missing Sources</Tag>
              </div>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card title="Recent Activity" bordered style={{ borderRadius: 12 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'flex', gap: 10, fontSize: 12 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ea580c', marginTop: 4 }} />
                <div>
                  <div><strong style={{ color: '#0f172a' }}>Tran Thi My Linh</strong> published Hue Royal Court Music</div>
                  <div style={{ color: '#94a3b8', fontSize: 11 }}>10 minutes ago</div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10, fontSize: 12 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#0284c7', marginTop: 4 }} />
                <div>
                  <div><strong style={{ color: '#0f172a' }}>System</strong> rebuilt the graph version v14</div>
                  <div style={{ color: '#94a3b8', fontSize: 11 }}>1 hour ago</div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10, fontSize: 12 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ea580c', marginTop: 4 }} />
                <div>
                  <div><strong style={{ color: '#0f172a' }}>Nguyen Hoang Nam</strong> edited Marble Mountains</div>
                  <div style={{ color: '#94a3b8', fontSize: 11 }}>2 hours ago</div>
                </div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}