"use client";

import { ErrorState } from "@/components/states";
import styles from "@/components/states/states.module.css";

export default function PublicError({ reset }: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className={styles.routeFrame}>
      <ErrorState
        title="Không thể tải trang"
        subTitle="Đã xảy ra sự cố khi tải nội dung. Vui lòng thử lại."
        retryLabel="Thử lại"
        onRetry={() => {
          document.getElementById("public-content")?.focus();
          reset();
        }}
        headingLevel={1}
      />
    </div>
  );
}
