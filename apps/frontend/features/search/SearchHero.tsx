import { SearchImage } from "@/features/search/SearchImage";
import styles from "@/features/search/search.module.css";

export function SearchHero({ image, fallbackImages = [] }: { image?: string | null; fallbackImages?: string[] }) {
  return <header className={styles.hero}>
    <div className={styles.heroArt} aria-hidden="true">{image && <SearchImage src={image} fallbacks={fallbackImages} sizes="100vw" priority />}</div>
    <div className={styles.heroShade} />
    <div className={styles.heroContent}>
      <h1>HERITAGE Virtual Tours</h1>
      <p>Discover our heritage in immersive experiences</p>
    </div>
  </header>;
}
