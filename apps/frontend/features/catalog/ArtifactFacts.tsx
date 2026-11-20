import type { CatalogContent } from "@/services/catalog.service";
import styles from "./artifact-facts.module.css";

const FACT_LABELS = {
  period: "Date / period",
  material: "Material",
  origin: "Origin",
  custodian: "Held at",
} as const;

export function ArtifactFacts({ item }: { item: CatalogContent }) {
  return <dl className={styles.facts}>{Object.entries(FACT_LABELS).map(([key, label]) => {
    const fact = item.metadata[key as keyof typeof FACT_LABELS];
    return fact ? <div key={key}><dt>{label}</dt><dd>
      <a href={fact.source_url} target="_blank" rel="noopener noreferrer">{fact.value}</a>
    </dd></div> : null;
  })}</dl>;
}
