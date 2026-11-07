import styles from "@/components/Loading/loading.module.css";

interface CircleLoadingProps {
  className?: string;
  label?: string;
}

const CircleLoading = ({
  className = "",
  label = "Loading…",
}: CircleLoadingProps) => {
  return (
    <div
      className={`${styles.circle} ${className}`}
      role="status"
      aria-label={label}
    >
      <span className={styles.spinner} aria-hidden="true" />
      <span className={styles.label} aria-hidden="true">{label}</span>
    </div>
  );
};

export default CircleLoading;
