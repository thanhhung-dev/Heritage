"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { PUBLIC_FOOTER_PATHS } from "@/config/public-footer";

export function PublicFooterSlot({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return PUBLIC_FOOTER_PATHS.includes(pathname) ? children : null;
}
