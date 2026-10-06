"use client";

import TriptychCard, { type TriptychCardData } from "@/components/TriptychCard/TriptychCard";
import PortraitCard, { type PortraitCardData } from "@/components/PortraitCard/PortraitCard";
import mockData from "@/mocks/heritage-mock.json";
import styles from "./preview.module.css";

export default function HeritagePreviewPage() {
  const items = mockData.slice(0, 5) as unknown as TriptychCardData[];

  return (
    <div className={styles.wrap}>
      <div className={styles.head}>
        <p className={styles.eyebrow}>HeritageGraph · Preview</p>
        <h1>Di sản Đà Nẵng — Huế</h1>
        <p>Triptych card · hover vào card để mở rộng hiện thông tin · 5 địa điểm đầu từ mock API</p>
      </div>

      <div className={styles.hero}>
        {items.map((item) => (
          <TriptychCard
            key={item.slug}
            item={item}
            exploreLabel="Khám phá"
            infoLabel="Chi tiết"
            onInfo={(slug) => window.alert(`Mở chi tiết: ${slug}`)}
          />
        ))}
      </div>

      <div className={styles.grid}>
        {items.map((item) => (
          <PortraitCard
            key={`portrait-${item.slug}`}
            item={item as unknown as PortraitCardData}
            exploreLabel="Khám phá"
            infoLabel="Chi tiết"
            onInfo={(slug) => window.alert(`Mở chi tiết: ${slug}`)}
          />
        ))}
      </div>
    </div>
  );
}