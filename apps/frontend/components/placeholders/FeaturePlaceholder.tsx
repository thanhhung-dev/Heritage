import type { PublicRoute } from "@/config/public-navigation";
import styles from "./feature-placeholder.module.css";

interface FeaturePlaceholderProps {
  route: PublicRoute;
}

export function FeaturePlaceholder({ route }: FeaturePlaceholderProps) {
  return (
    <section className={styles.page} aria-labelledby={`${route.key}-title`}>
      <div className={styles.content}>
        <p className={styles.eyebrow}>HeritageGraph Public Portal</p>
        <h1 id={`${route.key}-title`}>{route.title}</h1>
        <p className={styles.description}>{route.description}</p>
        <p className={styles.status} role="status">
          <span aria-hidden="true" />
          Đang hoàn thiện
        </p>
      </div>
    </section>
  );
}
