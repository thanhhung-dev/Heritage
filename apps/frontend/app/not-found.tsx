import { NotFoundState } from "@/components/states/NotFoundState";
import styles from "@/components/states/states.module.css";

export default function NotFound() {
  return (
    <main className={`${styles.routeFrame} ${styles.standaloneFrame}`}>
      <NotFoundState />
    </main>
  );
}
