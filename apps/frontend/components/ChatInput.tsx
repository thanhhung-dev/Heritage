"use client";

import { useState } from "react";
import type { AttachmentsProps } from "@ant-design/x";
import { Attachments, Sender } from "@ant-design/x";
import type { GetProp } from "antd";
import { CloudUploadOutlined } from "@ant-design/icons";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  loading?: boolean;
}

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  placeholder = "Nhắn tin...",
  loading,
}: ChatInputProps) {
  const [open, setOpen] = useState(false);

  const [items, setItems] = useState<GetProp<AttachmentsProps, "items">>([]);

  const handleAttachmentChange: AttachmentsProps["onChange"] = ({
    file,
    fileList,
  }) => {
    const updatedFileList = fileList.map((item) => {
      if (
        item.uid === file.uid &&
        file.status !== "removed" &&
        item.originFileObj
      ) {
        if (item.url?.startsWith("blob:")) {
          URL.revokeObjectURL(item.url);
        }

        return {
          ...item,
          url: URL.createObjectURL(item.originFileObj),
        };
      }

      return item;
    });

    setItems(updatedFileList);
  };

  const senderHeader = (
    <Sender.Header
      title="Tệp đính kèm"
      open={open}
      onOpenChange={setOpen}
    >
      <Attachments
        beforeUpload={() => false}
        items={items}
        onChange={handleAttachmentChange}
        placeholder={(type) =>
          type === "drop"
            ? {
                title: "Thả file vào đây",
              }
            : {
                icon: <CloudUploadOutlined />,
                title: "Tải file lên",
                description: "Click hoặc kéo thả file vào khu vực này",
              }
        }
      />
    </Sender.Header>
  );

  return (
    <Sender
      value={value}
      onChange={onChange}
      onSubmit={() => {
        if (value.trim() || items.length > 0) {
          onSubmit();
        }
      }}
      header={senderHeader}
      placeholder={placeholder}
      loading={loading}
    />
  );
}