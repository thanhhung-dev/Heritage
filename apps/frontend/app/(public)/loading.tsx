import { LoadingState } from "@/components/states";
import styles from "@/components/states/states.module.css";

export default function PublicLoading() {
  return <div className={styles.routeFrame}><LoadingState /></div>;
}
