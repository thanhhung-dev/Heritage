"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "antd";
import { ErrorState, LoadingState } from "@/components/states";
import { NotFoundState } from "@/components/states/NotFoundState";
import styles from "./route-states-preview.module.css";

type PreviewState = "loading" | "error" | "not-found";
const examples = [
  { key: "loading", label: "Loading" },
  { key: "error", label: "Error" },
  { key: "not-found", label: "404" },
] as const;

export function RouteStatesPreview() {
  const [state, setState] = useState<PreviewState>("loading");
  const [recovered, setRecovered] = useState(false);
  const recoveryRef = useRef<HTMLParagraphElement>(null);
  const exampleRef = useRef<HTMLDivElement>(null);
  const previousRecovery = useRef(recovered);

  useEffect(() => {
    if (state === "error" && previousRecovery.current !== recovered) {
      if (recovered) recoveryRef.current?.focus();
      else exampleRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
    }
    previousRecovery.current = recovered;
  }, [recovered, state]);

  return (
    <section className={styles.preview} aria-labelledby="route-states-preview-title">
      <h2 id="route-states-preview-title">Trạng thái trang</h2>
      <p>Minh họa giao diện. Loading và lỗi ở đây không phản ánh trạng thái tải trang thật.</p>
      <div className={styles.controls} role="group" aria-label="Chọn trạng thái minh họa">
        {examples.map((example) => (
          <Button key={example.key} aria-pressed={state === example.key} onClick={() => {
            setState(example.key);
            setRecovered(false);
          }}>{example.label}</Button>
        ))}
      </div>
      <div ref={exampleRef} className={styles.example}>
        {state === "loading" ? <LoadingState /> : null}
        {state === "error" ? recovered ? (
          <div className={styles.recovered}>
            <p ref={recoveryRef} tabIndex={-1} role="status">Đã thử lại ví dụ thành công. Trang hiện tại không được tải lại.</p>
            <Button onClick={() => setRecovered(false)}>Hiện lại ví dụ lỗi</Button>
          </div>
        ) : (
          <ErrorState headingLevel={3} title="Không thể tải trang" subTitle="Đã xảy ra sự cố khi tải nội dung. Vui lòng thử lại." retryLabel="Thử lại" onRetry={() => setRecovered(true)} />
        ) : null}
        {state === "not-found" ? <NotFoundState headingLevel={3} /> : null}
      </div>
    </section>
  );
}
