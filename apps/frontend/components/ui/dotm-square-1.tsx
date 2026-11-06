import type { CSSProperties } from "react";
import styles from "@/components/ui/dotm-square-1.module.css";

// Focused CSS Modules adaptation of Neon Drift by dot-matrix contributors.
// Source and license: https://github.com/zzzzshawn/matrix
interface DotmSquare1Props {
  size?: number;
  dotSize?: number;
  speed?: number;
  bloom?: boolean;
}

export function DotmSquare1({ size = 32, dotSize = 4, speed = 1.2, bloom = false }: DotmSquare1Props) {
  return (
    <span className={`${styles.matrix} ${bloom ? styles.bloom : ""}`} aria-hidden="true"
      style={{ width: size, height: size, "--dot-size": `${dotSize}px`, "--cycle": `${1500 / speed}ms` } as CSSProperties}>
      {Array.from({ length: 25 }, (_, index) => {
        const diagonal = Math.floor(index / 5) + 4 - index % 5;
        return <i key={index} className={styles.dot}
          style={{ "--delay": diagonal / 8 * 0.2 + diagonal % 2 * 0.5, "--rest-opacity": diagonal % 2 === 0 ? 0.88 : 0.14 } as CSSProperties} />;
      })}
    </span>
  );
}
