"use client";

import type { ReactNode, CSSProperties } from "react";
import styles from "./button.module.css";

export interface ButtonProps {
  children?: ReactNode;
  href?: string;
  onClick?: () => void;
  variant?: "primary" | "secondary";
  className?: string;
  style?: CSSProperties;
  target?: string;
}

export function Button({
  children = "Browse Library",
  href,
  onClick,
  variant = "primary",
  className,
  style,
  target,
}: ButtonProps) {
  const variantClass = styles[variant];
  const classes = [styles.btn, variantClass, className]
    .filter(Boolean)
    .join(" ");

  if (href) {
    return (
      <a
        href={href}
        target={target}
        rel={target === "_blank" ? "noopener" : undefined}
        className={classes}
        style={style}
        onClick={onClick}
      >
        {children}
      </a>
    );
  }

  return (
    <button type="button" className={classes} style={style} onClick={onClick}>
      {children}
    </button>
  );
}

export default Button;
