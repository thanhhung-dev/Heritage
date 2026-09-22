interface HeritageLogoProps {
  size?: number;
}

export function HeritageLogo({ size = 64 }: HeritageLogoProps) {
  const height = Math.round((size * 70) / 63);

  return (
    <svg
      width={size}
      height={height}
      viewBox="0 0 63 70"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <g clipPath="url(#clip0_168_148)">
        <mask
          id="mask0_168_148"
          style={{ maskType: "luminance" }}
          maskUnits="userSpaceOnUse"
          x="0"
          y="0"
          width="63"
          height="70"
        >
          <path
            d="M1.72887 25.8225C1.03346 23.8475 0.576935 21.5882 0.576935 19.3776C0.576935 17.1669 0.968 15.0395 1.66341 13.0793C1.68552 13.0373 1.68552 12.9953 1.70677 12.9541C4.48758 5.59129 11.8311 0.1689 19.9967 0.0642586H30.9194V38.7123H20.0052C11.7878 38.6077 4.44423 33.2685 1.72887 25.8225Z"
            fill="white"
          />

          <path
            d="M62.4035 0.0651002H20.8052V25.0554H62.4035V0.0651002Z"
            fill="white"
          />

          <path
            d="M25.1409 51.2083H0.57608V69.9045H25.1409V51.2083Z"
            fill="white"
          />

          <path
            d="M27.5153 14.1641L8.37482 34.6149L43.4786 67.4693L62.619 47.0185L27.5153 14.1641Z"
            fill="white"
          />
        </mask>

        <g mask="url(#mask0_168_148)">
          <path d="M63 0H0V14H63V0Z" fill="#FFAF01" />
          <path d="M63 14H0V28H63V14Z" fill="#FF8204" />
          <path d="M63 28H0V42H63V28Z" fill="#FA500F" />
          <path d="M63 42H0V56H63V42Z" fill="#E51300" />
          <path d="M63 56H0V70H63V56Z" fill="#C4001D" />
        </g>
      </g>

      <defs>
        <clipPath id="clip0_168_148">
          <rect width="63" height="70" fill="white" />
        </clipPath>
      </defs>
    </svg>
  );
}
