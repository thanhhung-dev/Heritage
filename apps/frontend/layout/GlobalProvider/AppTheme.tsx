"use client";
import { NeutralColors, PrimaryColors } from "@/styles/customTheme";
import { ThemeAppearance, createStyles } from "antd-style";
import GlobalStyle from "@/components/ThemeProvider/GlobalStyle"
import ConfigProvider from "@/components/ConfigProvider";
import FontLoader from "@/components/FontLoader";
import ThemeProvider from "@/components/ThemeProvider";
import { memo, useMemo, ReactNode } from "react";
import Image from 'next/image';
import Link from 'next/link';
import { tapestryTheme } from "@/styles/theme/tapestryTheme";

const FONT_CDN = "https://unpkg.com/@fontsource";

const defaultFonts = [
  `${FONT_CDN}/inter@5.3.0/400.css`,
  `${FONT_CDN}/inter@5.3.0/500.css`,
  `${FONT_CDN}/inter@5.3.0/600.css`,
  `${FONT_CDN}/inter@5.3.0/700.css`,
  `${FONT_CDN}/inter@5.3.0/800.css`,
  `${FONT_CDN}/poppins@5.3.0/400.css`,
  `${FONT_CDN}/poppins@5.3.0/600.css`,
];
export interface AppThemeProps {
    children?: ReactNode;
    customFontFamily?: string;
    customFontURL?: string;
    defaultAppearance?: ThemeAppearance;
    defaultNeutralColor?: NeutralColors;
    defaultPrimaryColor?: PrimaryColors;
    globalCDN?: boolean;
}

const useStyles = createStyles(({ css, token }) => ({
    app: css`
    position: relative;
    display: flex;
    flex-direction: column;
    width: 100%;
    background: #0a0e14;
    min-height: 100dvh;
    @media (min-width: 576px) {
      overflow: hidden;
    }
  `,
    // scrollbar-width and scrollbar-color are supported from Chrome 121
    // https://developer.mozilla.org/en-US/docs/Web/CSS/scrollbar-color
    scrollbar: css`
    scrollbar-color: ${token.colorFill} transparent;
    scrollbar-width: thin;

    #lobe-mobile-scroll-container {
      scrollbar-width: none;

      ::-webkit-scrollbar {
        width: 0;
        height: 0;
      }
    }
  `,

    // so this is a polyfill for older browsers
    scrollbarPolyfill: css`
    ::-webkit-scrollbar {
      width: 0.75em;
      height: 0.75em;
    }

    ::-webkit-scrollbar-thumb {
      border-radius: 10px;
    }

    :hover::-webkit-scrollbar-thumb {
      border: 3px solid transparent;
      background-color: ${token.colorText};
      background-clip: content-box;
    }

    ::-webkit-scrollbar-track {
      background-color: transparent;
    }
  `,
}));

const AppTheme = memo<AppThemeProps>(
    ({
        children,
        defaultAppearance,
        globalCDN,
        customFontURL,
        customFontFamily,
    }) => {
        const { styles, cx, theme } = useStyles();
        return (
            <ThemeProvider
                appearance="dark"
                themeMode="dark"
                className={cx(styles.app, styles.scrollbar, styles.scrollbarPolyfill)}
                defaultAppearance={defaultAppearance}
                customFonts={defaultFonts}
                theme={{
                    cssVar: { prefix: "ant" },
                    token: {
                        ...(tapestryTheme.token ?? {}),
                        fontFamily: customFontFamily
                            ? `${customFontFamily}, ${tapestryTheme.token?.fontFamily ?? theme.fontFamily}`
                            : (tapestryTheme.token?.fontFamily ?? theme.fontFamily),
                    },
                    components: tapestryTheme.components,
                }}
            >
                {!!customFontURL && <FontLoader url={customFontURL} />}
                <GlobalStyle />
                {/* <AntdStaticMethods /> */}
                <ConfigProvider
                    config={{
                        aAs: Link,
                        imgAs: Image,
                        imgUnoptimized: true,
                        proxy: globalCDN ? 'unpkg' : undefined,
                    }}
                >
                    {children}
                </ConfigProvider>
            </ThemeProvider>
        );
    }
);

AppTheme.displayName = 'AppTheme';

export default AppTheme;