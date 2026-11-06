import styles from "@/components/Loading/loading.module.css";

interface SkeletonLoadingProps {
  className?: string;
  label?: string;
  variant?: "article" | "cards";
}

/** Match the placeholder shape to the incoming article or portrait-card grid. */
const SkeletonLoading = ({
  className = "",
  label = "Đang tải nội dung…",
  variant = "article",
}: SkeletonLoadingProps) => (
  <div
    className={`${variant === "cards" ? styles.skeletonCards : styles.skeleton} ${className}`}
    role="status"
    aria-label={label}
  >
    {variant === "cards" ? (
      Array.from({ length: 10 }, (_, index) => (
        <div key={index} className={styles.skeletonCard} aria-hidden="true">
          <span className={styles.skeletonMedia} />
          <span className={styles.skeletonLine} />
          <span className={styles.skeletonLine} />
        </div>
      ))
    ) : (
      <div className={styles.skeletonBody} aria-hidden="true">
        <span className={styles.skeletonTitle} />
        {Array.from({ length: 8 }, (_, index) => (
          <span key={index} className={styles.skeletonLine} />
        ))}
      </div>
    )}
  </div>
);

export default SkeletonLoading;
