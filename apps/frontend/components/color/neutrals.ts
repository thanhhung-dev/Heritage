import {
  mauve as mauveBase,
  mauveDark,
  olive as oliveBase,
  oliveDark,
  sage as sageBase,
  sageDark,
  sand as sandBase,
  sandDark,
  slate as slateBase,
  slateDark,
} from "@radix-ui/colors";

export type NeutralPalette = {
  [index: number]: string;
  dark: string[];
};

const toIndexed = (
  name: string,
  base: Record<string, string>,
  dark: Record<string, string>,
): NeutralPalette => {
  const palette: Partial<NeutralPalette> = { dark: [] };
  for (let i = 1; i <= 12; i += 1) {
    palette[i] = base[`${name}${i}`];
    palette.dark![i] = dark[`${name}${i}`];
  }
  return palette as NeutralPalette;
};

export const mauve: NeutralPalette = toIndexed("mauve", mauveBase, mauveDark);
export const olive: NeutralPalette = toIndexed("olive", oliveBase, oliveDark);
export const sage: NeutralPalette = toIndexed("sage", sageBase, sageDark);
export const sand: NeutralPalette = toIndexed("sand", sandBase, sandDark);
export const slate: NeutralPalette = toIndexed("slate", slateBase, slateDark);