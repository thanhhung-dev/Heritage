'use client';

import React from 'react';
import { Button, Empty, Flex, Result, Spin, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

const panelStyle: React.CSSProperties = {
  minHeight: 200,
  padding: 32,
  textAlign: 'center',
};

interface LoadingStateProps {
  tip?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  tip = 'Đang tải dữ liệu di sản...',
  className = '',
}) => (
  <section className={className} role="status" aria-live="polite" aria-busy="true" aria-label={tip}>
    <Flex vertical align="center" justify="center" style={panelStyle}>
      <Spin size="large" tip={tip} />
    </Flex>
  </section>
);

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionText?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'Không có dữ liệu',
  description = 'Chưa tìm thấy bản ghi hoặc hiện vật di sản phù hợp.',
  actionText,
  onAction,
  className = '',
}) => (
  <section className={className} role="region" aria-label={title}>
    <Flex vertical align="center" justify="center" gap={12} style={panelStyle}>
      <Typography.Title level={5} style={{ margin: 0 }}>{title}</Typography.Title>
      <Empty description={<Typography.Text type="secondary">{description}</Typography.Text>}>
        {actionText && onAction ? (
          <Button type="primary" onClick={onAction}>
            {actionText}
          </Button>
        ) : null}
      </Empty>
    </Flex>
  </section>
);

interface ErrorStateProps {
  title?: string;
  subTitle?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Đã xảy ra lỗi kết nối',
  subTitle = 'Không thể đồng bộ dữ liệu với máy chủ di sản. Vui lòng thử lại sau.',
  onRetry,
  className = '',
}) => (
  <section className={className} role="alert">
    <Flex align="center" justify="center" style={panelStyle}>
      <Result
        status="error"
        title={title}
        subTitle={subTitle}
        extra={
          onRetry ? (
            <Button icon={<ReloadOutlined />} onClick={onRetry}>
              Thử lại
            </Button>
          ) : null
        }
      />
    </Flex>
  </section>
);
