"use client";

import { useState } from "react";
import { ShareAltOutlined } from "@ant-design/icons";
import type { ActionsFeedbackProps } from "@ant-design/x";
import { Actions } from "@ant-design/x";
import { message } from "antd";

interface ChatActionsProps {
  content: string;
}

export function ChatActions({ content }: ChatActionsProps) {
  // feedback
  const [feedbackStatus, setFeedbackStatus] =
    useState<ActionsFeedbackProps["value"]>("default");

  const onShare = async () => {
    try {
      if (navigator.share) {
        await navigator.share({ text: content });
      } else {
        await navigator.clipboard.writeText(content);
        message.success("Đã sao chép câu trả lời");
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      message.error("Không thể chia sẻ câu trả lời");
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
          onClick={() => void onShare()}
          label="share"
          defaultIcon={<ShareAltOutlined />}
        />
      ),
    },
  ];

  return <Actions items={items} />;
}
