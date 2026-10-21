'use client';

import { unstableSetRender } from 'antd';
import { useEffect } from 'react';
import { Root, createRoot } from 'react-dom/client';
import type { ReactElement } from 'react';

const AntdV5MonkeyPatch = () => {
  useEffect(() => {
    unstableSetRender((node: ReactElement, container: Element | DocumentFragment) => {
      const root: Root = createRoot(container);
      root.render(node);
      return async () => {
        root.unmount();
      };
    });
  }, []);
  return null;
};

export default AntdV5MonkeyPatch;