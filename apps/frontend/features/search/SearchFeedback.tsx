import { CloseCircleOutlined, ReloadOutlined, WarningOutlined } from "@ant-design/icons";
import styles from "@/features/search/search.module.css";

export function SearchFeedback({ error = false, onRetry }: { error?: boolean; onRetry: () => void }) {
  return <div className={styles.feedback} role={error ? "alert" : "status"}>
    {error ? <WarningOutlined className={styles.feedbackIcon} aria-hidden /> : <CloseCircleOutlined className={styles.feedbackIcon} aria-hidden />}
    <p>{error ? "We couldn’t load the tours. Please try again." : "No tours found matching your filters"}</p>
    {error && <button className={styles.retryButton} type="button" onClick={onRetry}><ReloadOutlined /> Try again</button>}
  </div>;
}
