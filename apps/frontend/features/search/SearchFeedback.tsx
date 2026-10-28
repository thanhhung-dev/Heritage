import { ReloadOutlined, SearchOutlined, WarningOutlined } from "@ant-design/icons";
import styles from "./search.module.css";

interface SearchFeedbackProps {
  error?: boolean;
  filtered: boolean;
  onRetry: () => void;
  onReset: () => void;
}

export function SearchFeedback({ error = false, filtered, onRetry, onReset }: SearchFeedbackProps) {
  const description = error
    ? "Kết nối có thể đang gián đoạn. Hãy thử lại sau ít phút; tìm kiếm và bộ lọc của bạn vẫn được giữ nguyên."
    : filtered
      ? "Thử một từ khóa khác hoặc mở rộng bộ lọc để tiếp tục khám phá."
      : "Chưa có di sản được công bố. Hãy quay lại sau để khám phá những câu chuyện mới.";
  return (
    <div className={styles.feedback} role={error ? "alert" : "status"}>
      <span className={styles.feedbackIcon}>
        {error ? <WarningOutlined aria-hidden /> : <SearchOutlined aria-hidden />}
      </span>
      <h3>{error ? "Chưa thể tải kết quả" : "Không tìm thấy di sản phù hợp"}</h3>
      <p>{description}</p>
      {error ? (
        <button className={styles.primaryButton} type="button" onClick={onRetry}>
          <ReloadOutlined aria-hidden /> Thử lại
        </button>
      ) : filtered && (
        <button className={styles.primaryButton} type="button" onClick={onReset}>
          Xóa tìm kiếm và bộ lọc
        </button>
      )}
    </div>
  );
}
