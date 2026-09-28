"use client";

import { useEffect, useMemo, useState } from "react";
import type { ThemeConfig } from "antd";
import { theme as antdTheme } from "antd";

type ThemeTokens = NonNullable<ThemeConfig["token"]>;

function readCssToken(
  styles: CSSStyleDeclaration,
  name: string,
  visited = new Set<string>(),
): string {
  if (visited.has(name)) return "";

  visited.add(name);
  const value = styles.getPropertyValue(name).trim();

  return value.replace(/var\((--[\w-]+)\)/g, (_, nestedName: string) =>
    readCssToken(styles, nestedName, visited),
  );
}

export function useHeritageTheme(): ThemeConfig {
  const [resolvedTokens, setResolvedTokens] = useState<ThemeTokens>({});

  useEffect(() => {
    const styles = getComputedStyle(document.documentElement);
    const radius = Number.parseFloat(readCssToken(styles, "--radius-md"));

    setResolvedTokens({
      colorPrimary: readCssToken(styles, "--accent"),
      colorBgBase: readCssToken(styles, "--bg"),
      colorTextBase: readCssToken(styles, "--text"),
      borderRadius: Number.isFinite(radius) ? radius : undefined,
      fontFamily: readCssToken(styles, "--font-sans"),
    });
  }, []);

  return useMemo(
    () => ({
      algorithm: antdTheme.darkAlgorithm,
      token: resolvedTokens,
    }),
    [resolvedTokens],
  );
}
