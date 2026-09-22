"use client";

import { useState } from "react";
import { CheckOutlined, ShareAltOutlined } from "@ant-design/icons";
import type { ActionsFeedbackProps } from "@ant-design/x";
import { Actions } from "@ant-design/x";
import { message } from "antd";

type ActionStatus = "default" | "loading" | "running" | "error";

interface ChatActionsProps {
  content: string;
}

export function ChatActions({ content }: ChatActionsProps) {
  // feedback
  const [feedbackStatus, setFeedbackStatus] =
    useState<ActionsFeedbackProps["value"]>("default");

  // audio
  const [audioStatus, setAudioStatus] = useState<ActionStatus>("default");
  // share
  const [shareStatus, setShareStatus] = useState<ActionStatus>("default");

  const onClick = (type: "share" | "audio") => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    const dispatchFN = type === "share" ? setShareStatus : setAudioStatus;
    const status = type === "share" ? shareStatus : audioStatus;
    switch (status) {
      case "default":
        dispatchFN("loading");
        timer = setTimeout(() => {
          timer && clearTimeout(timer);
          dispatchFN("running");
        }, 1500);
        break;
      case "running":
        dispatchFN("loading");
        timer = setTimeout(() => {
          timer && clearTimeout(timer);
          dispatchFN("default");
        }, 1500);
        break;
    }
  };

  const items = [
    {
      key: "feedback",
      actionRender: () => (
        <Actions.Feedback
          value={feedbackStatus}
          onChange={(val) => {
            setFeedbackStatus(val);
            message.success(
              val === "like"
                ? "Bạn đã thích câu trả lời"
                : "Bạn đã không thích câu trả lời"
            );
          }}
        />
      ),
    },
    {
      key: "copy",
      label: "copy",
      actionRender: () => <Actions.Copy text={content} />,
    },
    {
      key: "share",
      label: "share",
      actionRender: () => (
        <Actions.Item
          onClick={() => onClick("share")}
          label={shareStatus}
          status={shareStatus}
          defaultIcon={<ShareAltOutlined />}
          runningIcon={<CheckOutlined />}
        />
      ),
    },
  ];

  return <Actions items={items} />;
}