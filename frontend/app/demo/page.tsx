"use client";
'use client';

import { createStyles } from 'antd-style';
import { Button } from 'antd';

const useStyles = createStyles(({ token, stylish, css }) => ({
  wrapper: css`
    padding: 40px;
    background: ${token.colorBgBase};
    color: ${token.colorText};
  `,
  glass: stylish.glassPanel,
  gradientBtn: stylish.gradientButton,
}));

export default function Demo() {
  const { styles } = useStyles();
  return (
    <div className={styles.wrapper}>
      <h1>Tapestry Theme</h1>
      <div className={styles.glass} style={{ padding: 20, marginBottom: 16 }}>
        Glass panel
      </div>
      <Button type="primary">Antd Button (cam)</Button>
      <button className={styles.gradientBtn} style={{ padding: '10px 24px', marginLeft: 12 }}>
        Custom gradient
      </button>
    </div>
  );
}
