"use client";

import Image from "next/image";
import Link from "next/link";
import { ConfigProvider, Modal, theme } from "antd";
import type { CatalogContent } from "@/services/catalog.service";
import { ArtifactFacts } from "./ArtifactCollectionSection";
import styles from "./ArtifactCollectionSection.module.css";

export function CatalogInfoModal({ item, onClose }: { item: CatalogContent | null; onClose: () => void }) {
  return <ConfigProvider theme={{ algorithm: theme.darkAlgorithm, token: { colorPrimary: "#e3b273" } }}>
    <Modal open={item !== null} title={item?.title} onCancel={onClose} centered destroyOnHidden
      footer={item ? <Link href={item.href}>Khám phá nội dung →</Link> : null}>
      {item && <div className={styles.modalSummary}>
        {item.card_image_url && <Image src={item.card_image_url} alt={item.title} width={800} height={450}
          unoptimized className={styles.modalImage} />}
        {item.region && <p>{item.region}</p>}
        {item.description && <p>{item.description}</p>}
        <ArtifactFacts item={item} />
        {item.source_url && <a href={item.source_url} target="_blank" rel="noopener noreferrer">Nguồn tư liệu</a>}
      </div>}
    </Modal>
  </ConfigProvider>;
}
