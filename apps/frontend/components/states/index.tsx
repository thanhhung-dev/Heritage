'use client';

import React from 'react';
import { Spin, Empty, Button, Result } from 'antd';
import { LoadingOutlined, ReloadOutlined } from '@ant-design/icons';
import styles from './states.module.css';

interface LoadingStateProps {
  tip?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  tip = 'Đang tải…',
  className = '',
}) => (
  <div className={`${styles.loading} ${className}`} role="status" aria-live="polite" aria-atomic="true">
    <span className={styles.srOnly}>{tip}</span>
    <span aria-hidden="true"><Spin size="large" indicator={<LoadingOutlined spin />} /></span>
  </div>
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
  <div className={`${styles.empty} ${className}`}>
    <Empty description={<span className={styles.description}>{description}</span>}>
      {actionText && onAction && (
        <Button type="primary" onClick={onAction} className={styles.primaryAction}>
          {actionText}
        </Button>
      )}
    </Empty>
  </div>
);

interface ErrorStateProps {
  title?: string;
  subTitle?: string;
  onRetry?: () => void;
  retryLabel?: string;
  headingLevel?: 1 | 2 | 3;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Đã xảy ra lỗi kết nối',
  subTitle = 'Không thể đồng bộ dữ liệu với máy chủ di sản. Vui lòng thử lại sau.',
  onRetry,
  retryLabel = 'Tải lại trang',
  headingLevel = 2,
  className = '',
}) => {
  const Heading = headingLevel === 1 ? 'h1' : headingLevel === 2 ? 'h2' : 'h3';
  return (
    <div className={`${styles.error} ${className}`} role="alert">
      <Result
        status="error"
        title={<Heading className={styles.title}>{title}</Heading>}
        subTitle={<span className={styles.description}>{subTitle}</span>}
        extra={
          onRetry && (
            <Button icon={<ReloadOutlined aria-hidden="true" />} onClick={onRetry} className={styles.retryAction}>
              {retryLabel}
            </Button>
          )
        }
      />
    </div>
  );
};
