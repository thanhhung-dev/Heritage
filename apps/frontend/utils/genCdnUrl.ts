export type CDN = "unpkg" | "aliyun" | "jsdelivr" | "npm";

export interface CdnApi {
  path: string;
  pkg: string;
  version?: string;
  proxy?: CDN;
  useDefaultVersion?: boolean;
}

const DEFAULT_VERSION = "latest";

const isStableVersion = (version?: string) => version && version !== "latest";

export const genCdnUrl = ({ pkg, path, proxy = "unpkg", version }: CdnApi) => {
  const v = isStableVersion(version) ? version : DEFAULT_VERSION;
  switch (proxy) {
    case "aliyun":
      return `https://registry.npmmirror.com/${pkg}/${v}/files/${path}`;
    case "jsdelivr":
      return `https://cdn.jsdelivr.net/npm/${pkg}@${v}/${path}`;
    case "npm":
    default:
      return `https://unpkg.com/${pkg}@${v}/${path}`;
  }
};