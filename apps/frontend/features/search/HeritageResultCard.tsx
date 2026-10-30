import Link from "next/link";
import { ClockCircleOutlined } from "@ant-design/icons";
import { formatSearchDuration, heritageLanguages } from "@/features/search/catalogue";
import { SearchImage } from "@/features/search/SearchImage";
import type { HeritageSearchItem } from "@/features/search/types";
import styles from "@/features/search/search.module.css";

export function HeritageResultCard({ item, recommendation = false }: { item: HeritageSearchItem; recommendation?: boolean }) {
  const languages = heritageLanguages(item);
  const duration = formatSearchDuration(item.duration_seconds);
  return <article className={recommendation ? styles.recommendationCard : styles.resultCard} data-tour-result={!recommendation || undefined}>
    <Link className={styles.cardLink} href={`/content/${encodeURIComponent(item.slug)}`} prefetch={false}>
      <div className={styles.cardImage}><SearchImage src={item.card_image_url ?? item.splash_image_url} sizes={recommendation ? "(max-width: 600px) 65vw, 20vw" : "96px"} /></div>
      <div className={styles.cardBody}>
        <h3>{item.headline || item.title}</h3>
        {item.region && <p className={styles.cardRegion}>{item.region}</p>}
        {!recommendation && <>
          {languages.length > 0 && <p className={styles.cardLanguages}>{languages.join(", ")}</p>}
          <p className={styles.cardDescription}>{item.tagline || item.description || "Explore this heritage through an immersive virtual tour."}</p>
          <div className={styles.cardBadges}>
            {languages[0] && <span className={styles.languageBadge}>{languages[0]}</span>}
            {duration && <span className={styles.durationBadge}><ClockCircleOutlined aria-hidden /> {duration}</span>}
          </div>
        </>}
      </div>
    </Link>
  </article>;
}
