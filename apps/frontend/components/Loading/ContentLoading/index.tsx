import styles from "@/components/Loading/loading.module.css";

interface ContentLoadingProps {
  className?: string;
  label?: string;
}

/** Compact loading for a content region; keeps the surrounding page visible. */
const ContentLoading = ({
  className = "",
  label = "Loading Content…",
}: ContentLoadingProps) => (
  <div
    className={`${styles.content} ${className}`}
    role="status"
    aria-label={label}
  >
    <span className={styles.spinner} aria-hidden="true" />
  </div>
);

export default ContentLoading;
