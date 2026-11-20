/* eslint-disable @next/next/no-img-element -- Keep exported SVG intrinsic dimensions, including fractional sizes. */
import { designAssets, type DesignAssetName } from "./design-assets";
import styles from "./knowledge.module.css";

export function DesignIcon({ name }: { name: DesignAssetName }) {
  return <span aria-hidden="true" className={styles.icon}><img src={designAssets[name].src} alt="" /></span>;
}

export function KnowledgeBrand() {
  return <span className={styles.brand}>
    <span className={styles.logoSlot} aria-hidden="true"><span className={styles.logoNative}>
      <img src={designAssets["library-Group1"].src} alt="" />
    </span></span>
    <strong>HERITAGE</strong>
  </span>;
}
