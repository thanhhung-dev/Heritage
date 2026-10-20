import Link from "next/link";
import { PUBLIC_ROUTE_BY_KEY } from "@/config/public-navigation";
import styles from "./states.module.css";

interface NotFoundStateProps {
  headingLevel?: 1 | 2 | 3;
}

export function NotFoundState({ headingLevel = 1 }: NotFoundStateProps) {
  const Heading = headingLevel === 1 ? "h1" : headingLevel === 2 ? "h2" : "h3";
  return (
    <section className={styles.notFound}>
      <p className={styles.code}>404</p>
      <Heading className={styles.title}>Không tìm thấy trang</Heading>
      <p className={styles.description}>Trang bạn tìm kiếm không tồn tại hoặc đã được chuyển sang địa chỉ khác.</p>
      <Link className={styles.homeLink} href={PUBLIC_ROUTE_BY_KEY.home.href}>Về trang chủ</Link>
    </section>
  );
}
