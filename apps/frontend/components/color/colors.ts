import {
  blue as blueBase,
  blueDark,
  cyan as cyanBase,
  cyanDark,
  geekblue as geekblueBase,
  geekblueDark,
  gold as goldBase,
  goldDark,
  green as greenBase,
  greenDark,
  lime as limeBase,
  limeDark,
  magenta as magentaBase,
  magentaDark,
  orange as orangeBase,
  orangeDark,
  purple as purpleBase,
  purpleDark,
  red as redBase,
  redDark,
  volcano as volcanoBase,
  volcanoDark,
  yellow as yellowBase,
  yellowDark,
} from "@ant-design/colors";

export type Palette = {
  [index: number]: string;
  dark: string[];
};

export const red: Palette = { ...redBase, dark: redDark };
export const volcano: Palette = { ...volcanoBase, dark: volcanoDark };
export const orange: Palette = { ...orangeBase, dark: orangeDark };
export const gold: Palette = { ...goldBase, dark: goldDark };
export const yellow: Palette = { ...yellowBase, dark: yellowDark };
export const lime: Palette = { ...limeBase, dark: limeDark };
export const green: Palette = { ...greenBase, dark: greenDark };
export const cyan: Palette = { ...cyanBase, dark: cyanDark };
export const blue: Palette = { ...blueBase, dark: blueDark };
export const geekblue: Palette = { ...geekblueBase, dark: geekblueDark };
export const purple: Palette = { ...purpleBase, dark: purpleDark };
export const magenta: Palette = { ...magentaBase, dark: magentaDark };