import HeritageText from "@/components/HeritageText";
import { HeritageLogoMini } from "@/components/Logo/HeritageLogoMinimal";
import styles from "@/components/Loading/loading.module.css";

interface BrandTextLoadingProps {
  className?: string;
  label?: string;
  debugId?: string;
}

/** Full-page loading with Heritage branding, not a content-region placeholder. */
const BrandTextLoading = ({
  className = "",
  label = ":Loading…",
  debugId,
}: BrandTextLoadingProps) => {
  const showDebug = process.env.NODE_ENV === "development" && debugId;

  return (
    <div className={`${styles.brandContainer} ${className}`}>
      <div className={styles.brandStatus} role="status" aria-label={label}>
        <div className={styles.brand} aria-hidden="true">
          <HeritageLogoMini size={48} />
          <HeritageText size={28} />
        </div>
        <span className={styles.brandTrack} aria-hidden="true" />
        <span className={styles.label} aria-hidden="true">{label}</span>
      </div>
      {showDebug && (
        <div className={styles.debug}>
          <code>Debug ID: {debugId}</code>
          <span>Chỉ hiển thị trong development</span>
        </div>
      )}
    </div>
  );
};

export default BrandTextLoading;
