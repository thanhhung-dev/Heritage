"use client";
import { NeutralColors, PrimaryColors } from "@/styles/customTheme";
import { ThemeAppearance, createStyles } from "antd-style";
import GlobalStyle from "@/components/ThemeProvider/GlobalStyle"
import ConfigProvider from "@/components/ConfigProvider";
import FontLoader from "@/components/FontLoader";
import ThemeProvider from "@/components/ThemeProvider";
import { memo, ReactNode } from "react";
import Image from 'next/image';
import Link from 'next/link';
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
    background: #FFF;
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
                appearance="light"
                themeMode="light"
                className={cx(styles.app, styles.scrollbar, styles.scrollbarPolyfill)}
                // customTheme={{
                //     neutralColor: neutralColor ?? defaultNeutralColor,
                //     primaryColor: primaryColor ?? defaultPrimaryColor,
                // }}
                defaultAppearance={defaultAppearance}
                theme={{
                    cssVar: { prefix: "ant" },
                    token: {
                        fontFamily: customFontFamily ? `${customFontFamily},${theme.fontFamily}` : undefined,
                    },
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