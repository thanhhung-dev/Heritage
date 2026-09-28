"use client";

import { ElementType, ReactNode, createContext, memo } from "react";
import { useContext } from "react";

import { CDN, CdnApi, genCdnUrl } from "@/utils/genCdnUrl";

export interface Config {
  aAs?: ElementType;
  customCdnFn?: CdnFn;
  imgAs?: ElementType;
  imgUnoptimized?: boolean;
  proxy?: CDN | "custom";
}

export const ConfigContext = createContext<Config | null>(null);

const ConfigProvider = memo<{ children: ReactNode; config: Config }>(
  ({ children, config }) => {
    return <ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>;
  }
);

ConfigProvider.displayName = 'ConfigProvider';

// useCdnFn
export type CdnFn = ({ pkg, version, path }: CdnApi) => string;

const cdnFallback: CdnFn = ({ pkg, version, path }) =>
  genCdnUrl({ path, pkg, proxy: "aliyun", version });

export const useCdnFn = (): CdnFn => {
  const config = useContext(ConfigContext);
  if (!config) return cdnFallback;
  if (config?.proxy !== "custom")
    return ({ pkg, version, path }) =>
      genCdnUrl({ path, pkg, proxy: config.proxy as CDN, version });
  return config?.customCdnFn || cdnFallback;
};

export default ConfigProvider;