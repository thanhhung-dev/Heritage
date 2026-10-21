'use client';

import { ReactNode } from "react";
import StyleRegistry from "@/layout/GlobalProvider/StyleRegistry";
import AppTheme from "./AppTheme";
import { appEnv } from "@/envs/app";
import AntdV5MonkeyPatch from "./AntdV5MonkeyPatch";
import type { NeutralColors, PrimaryColors } from "@/styles/customTheme";

interface GlobalLayoutProps {
  children: ReactNode;
  appearance: string;
  neutralColor?: string;
  primaryColor?: string;
  variants?: string;
}

const GlobalLayout = ({
  children,
  neutralColor,
  primaryColor,
  appearance,
}: GlobalLayoutProps) => {
  return (
    <StyleRegistry>
      <AppTheme
        customFontFamily={appEnv.NEXT_PUBLIC_CUSTOM_FONT_FAMILY}
        customFontURL={appEnv.NEXT_PUBLIC_CUSTOM_FONT_URL}
        defaultAppearance={appearance}
        defaultNeutralColor={neutralColor as NeutralColors | undefined}
        defaultPrimaryColor={primaryColor as PrimaryColors | undefined}
        globalCDN={appEnv.NEXT_PUBLIC_CDN_USE_GLOBAL}
      >
        {children}
      </AppTheme>
      <AntdV5MonkeyPatch />
    </StyleRegistry>
  );
}

export default GlobalLayout;