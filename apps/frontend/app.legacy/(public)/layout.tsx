import type { ReactNode } from "react";
import { PublicShell } from "@/components/public-shell/PublicShell";
import { PublicAccountProvider } from "@/features/account/PublicAccountProvider";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <PublicAccountProvider>
      <PublicShell>{children}</PublicShell>
    </PublicAccountProvider>
  );
}
