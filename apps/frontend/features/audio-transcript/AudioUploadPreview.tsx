'use client';

import React, { useEffect, useState } from 'react';
import {
  App,
  Button,
  Col,
  Row,
  Space,
  Typography,
  Upload,
} from 'antd';
import type { UploadProps } from 'antd';
import {
  CheckCircleOutlined,
  CloudUploadOutlined,
  DeleteOutlined,
  FolderOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  RightOutlined,
  SoundOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Dragger } = Upload;

interface AudioPreviewItem {
  uid: string;
  name: string;
  size: number;
  type: string;
  previewUrl: string;
  duration: number | null;
  uploadedAt: string;
}

const ACCEPTED_TYPES = ['audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/x-m4a', 'audio/ogg'];
const MAX_SIZE_MB = 50;

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null || Number.isNaN(seconds)) return '--:--';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export default function AudioUploadPreview() {
  const { message } = App.useApp();
  const [audioItem, setAudioItem] = useState<AudioPreviewItem | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    return () => {
      if (audioItem?.previewUrl) {
        URL.revokeObjectURL(audioItem.previewUrl);
      }
    };
  }, [audioItem]);

  const handleFileSelect = (file: File) => {
    const isValidExt = /\.(mp3|wav|m4a|ogg)$/i.test(file.name);
    if (!ACCEPTED_TYPES.includes(file.type) && !isValidExt) {
      message.error('Ch? h? tr? ??nh d?ng ?m thanh MP3, WAV, M4A ho?c OGG.');
      return Upload.LIST_IGNORE;
    }

    if (file.size / 1024 / 1024 > MAX_SIZE_MB) {
      message.error(`Dung l??ng file kh?ng ???c v??t qu? ${MAX_SIZE_MB}MB.`);
      return Upload.LIST_IGNORE;
    }

    if (audioItem?.previewUrl) {
      URL.revokeObjectURL(audioItem.previewUrl);
    }

    const previewUrl = URL.createObjectURL(file);
    const newItem: AudioPreviewItem = {
      uid: `${Date.now()}`,
      name: file.name,
      size: file.size,
      type: file.type || 'audio/mpeg',
      previewUrl,
      duration: null,
      uploadedAt: new Date().toLocaleTimeString('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
      }),
    };

    setAudioItem(newItem);
    message.success(`?? t?i "${file.name}" l?n tr?nh xem tr??c.`);
    return false;
  };

  const handleRemove = () => {
    if (audioItem?.previewUrl) {
      URL.revokeObjectURL(audioItem.previewUrl);
    }
    setAudioItem(null);
    message.info('?? x?a file ?m thanh kh?i h?ng ??i.');
  };

  const handleMockSave = () => {
    if (!audioItem) return;
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      message.success('?? x?c nh?n b?n ghi ?m. S?n s?ng chuy?n sang b??c g?n transcript (HER-310).');
    }, 450);
  };

  const uploadProps: UploadProps = {
    name: 'audio',
    multiple: false,
    showUploadList: false,
    accept: '.mp3,.wav,.m4a,.ogg,audio/*',
    beforeUpload: handleFileSelect,
  };

  return (
    <div
      style={{
        background: '#ffffff',
        minHeight: '100vh',
        width: '100%',
        padding: '24px 32px 48px',
        color: '#111827',
        boxSizing: 'border-box',
      }}
    >
      <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 14 }}>
        Audio &amp; Transcript <span style={{ margin: '0 6px' }}>/</span>
        Cloudflare R2 <span style={{ margin: '0 6px' }}>/</span>
        Drafts <span style={{ margin: '0 6px' }}>/</span>
        <span style={{ color: '#4b5563' }}>Upload audio</span>
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 16,
          gap: 16,
        }}
      >
        <div>
          <Title level={3} style={{ margin: 0, fontWeight: 600, color: '#111827', fontSize: 20 }}>
            Upload audio
          </Title>
          <Text style={{ color: '#6b7280', fontSize: 13 }}>
            Store original narration audio in Cloudflare R2, then verify playback before attaching timestamped transcripts.
          </Text>
        </div>

        <Button
          icon={<ReloadOutlined style={{ color: audioItem ? '#111827' : '#9ca3af', fontSize: 12 }} />}
          onClick={handleRemove}
          disabled={!audioItem}
          style={{
            borderRadius: 8,
            borderColor: '#e5e7eb',
            background: '#ffffff',
            height: 32,
            paddingInline: 14,
            fontSize: 13,
          }}
        >
          <span style={{ color: audioItem ? '#111827' : '#9ca3af' }}>Reset queue</span>
        </Button>
      </div>

      <div
        style={{
          padding: '10px 0',
          borderTop: '1px solid #f3f4f6',
          borderBottom: '1px solid #f3f4f6',
          marginBottom: 20,
          fontSize: 12,
          color: '#6b7280',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexWrap: 'wrap',
        }}
      >
        <Text strong style={{ fontSize: 11, letterSpacing: 0.4, color: '#374151' }}>
          PREVIEW MODE
        </Text>
        <span>
          Client-side playback only ? Supported formats: MP3, WAV, M4A, OGG (up to {MAX_SIZE_MB}MB) ? Ready for R2 storage integration.
        </span>
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 14,
        }}
      >
        <Space size={6} style={{ fontSize: 13, color: '#374151' }}>
          <FolderOutlined style={{ color: '#4b5563' }} />
          <Text strong style={{ color: '#111827', fontSize: 13 }}>
            Cloudflare R2
          </Text>
          <RightOutlined style={{ fontSize: 10, color: '#9ca3af' }} />
          <span style={{ color: '#4b5563' }}>heritage-audio-demo</span>
          <RightOutlined style={{ fontSize: 10, color: '#9ca3af' }} />
          <Text strong style={{ color: '#111827', fontSize: 13 }}>
            Drafts
          </Text>
        </Space>

        <span style={{ fontSize: 12, color: '#6b7280' }}>
          Destination bucket: <strong style={{ color: '#374151' }}>Drafts</strong>
        </span>
      </div>

      <div style={{ marginBottom: 28 }}>
        <Dragger
          {...uploadProps}
          styles={{
            root: { background: '#ffffff' },
          }}
          style={{
            background: '#ffffff',
            border: '1px dashed #d1d5db',
            borderRadius: 12,
            padding: '28px 20px',
          }}
        >
          <p style={{ marginBottom: 8 }}>
            <CloudUploadOutlined style={{ color: '#374151', fontSize: 26 }} />
          </p>
          <p style={{ fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 4 }}>
            Drag and drop audio file here
          </p>
          <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 16 }}>
            Select MP3, WAV, M4A, or OGG files (max {MAX_SIZE_MB}MB).
          </p>
          <Button
            type="primary"
            style={{
              background: '#18181b',
              borderColor: '#18181b',
              borderRadius: 8,
              height: 32,
              paddingInline: 16,
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            <span style={{ color: '#ffffff' }}>Choose file</span>
          </Button>
        </Dragger>
      </div>

      <div style={{ marginBottom: 24 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 12,
          }}
        >
          <Text strong style={{ fontSize: 15, color: '#111827' }}>
            Upload queue &amp; Player preview
          </Text>
          <Text style={{ fontSize: 12, color: '#6b7280' }}>
            {audioItem ? '1 file ? 1 completed ? Ready to play' : '0 files ? Waiting for audio upload'}
          </Text>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 220px 110px',
            padding: '8px 12px',
            borderBottom: '1px solid #f3f4f6',
            fontSize: 12,
            color: '#9ca3af',
          }}
        >
          <span>File</span>
          <span>Upload status</span>
          <span style={{ textAlign: 'right' }}>Actions</span>
        </div>

        {!audioItem ? (
          <div
            style={{
              padding: '28px 16px',
              borderBottom: '1px solid #f3f4f6',
              textAlign: 'center',
              color: '#6b7280',
              fontSize: 13,
            }}
          >
            No audio file in queue. Drag and drop or click <strong>Choose file</strong> above to preview playback.
          </div>
        ) : (
          <div style={{ borderBottom: '1px solid #f3f4f6', padding: '16px 12px' }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 220px 110px',
                alignItems: 'center',
                gap: 12,
                marginBottom: 14,
              }}
            >
              <Space size={12}>
                <SoundOutlined style={{ fontSize: 16, color: '#4b5563' }} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>
                    {audioItem.name}
                  </div>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>
                    {audioItem.type.split('/')[1]?.toUpperCase() || 'AUDIO'} ? {formatBytes(audioItem.size)} ? Duration {formatDuration(audioItem.duration)}
                  </div>
                </div>
              </Space>

              <div>
                <div style={{ fontSize: 12, fontWeight: 500, color: '#111827', marginBottom: 4 }}>
                  <CheckCircleOutlined style={{ color: '#111827', marginRight: 6 }} />
                  Completed
                </div>
                <div
                  style={{
                    height: 3,
                    width: '100%',
                    background: '#18181b',
                    borderRadius: 2,
                    marginBottom: 4,
                  }}
                />
                <div style={{ fontSize: 11, color: '#6b7280' }}>
                  Loaded in browser ? Draft ({audioItem.uploadedAt})
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <Button
                  icon={<DeleteOutlined style={{ color: '#111827', fontSize: 12 }} />}
                  onClick={handleRemove}
                  style={{
                    borderRadius: 8,
                    borderColor: '#e5e7eb',
                    background: '#ffffff',
                    height: 30,
                    fontSize: 12,
                  }}
                >
                  <span style={{ color: '#111827' }}>Remove</span>
                </Button>
              </div>
            </div>

            <div
              style={{
                padding: '10px 14px',
                background: '#fafafa',
                border: '1px solid #e5e7eb',
                borderRadius: 10,
              }}
            >
              <audio
                controls
                src={audioItem.previewUrl}
                style={{ width: '100%', height: 36 }}
                onLoadedMetadata={(e) => {
                  const dur = e.currentTarget.duration;
                  setAudioItem((prev) => (prev ? { ...prev, duration: dur } : null));
                }}
              />
            </div>
          </div>
        )}
      </div>

      <Row gutter={[16, 16]} align="stretch">
        <Col xs={24} lg={16}>
          <div
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: 12,
              padding: '18px 20px',
              background: '#ffffff',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 15, fontWeight: 600, color: '#111827', marginBottom: 2 }}>
                Confirm audio track for transcript editing
              </div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>
                {audioItem
                  ? `${audioItem.name} ? Revision 1`
                  : 'No audio file selected yet ? Revision 1'}
              </div>
            </div>

            <Row gutter={[16, 12]} style={{ marginBottom: 16 }}>
              <Col xs={24} sm={12}>
                <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>Audio title</div>
                <div style={{ fontSize: 13, fontWeight: 500, color: '#111827' }}>
                  {audioItem ? audioItem.name.replace(/\.[^/.]+$/, '') : 'Waiting for audio upload'}
                </div>
              </Col>
              <Col xs={24} sm={12}>
                <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>
                  Transcript / Publication
                </div>
                <div style={{ fontSize: 13, fontWeight: 500, color: '#111827' }}>
                  {audioItem ? 'Draft - Audio verified' : 'Draft - Not uploaded'}
                </div>
              </Col>
            </Row>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: 12,
                flexWrap: 'wrap',
              }}
            >
              <span style={{ fontSize: 12, color: '#6b7280' }}>
                Verify sound quality and duration before attaching timestamped captions (HER-310).
              </span>
              <Button
                type="primary"
                loading={saving}
                disabled={!audioItem}
                onClick={handleMockSave}
                style={{
                  background: audioItem ? '#18181b' : '#f3f4f6',
                  borderColor: audioItem ? '#18181b' : '#e5e7eb',
                  borderRadius: 8,
                  height: 34,
                  paddingInline: 16,
                  fontSize: 13,
                  fontWeight: 500,
                }}
              >
                <span style={{ color: audioItem ? '#ffffff' : '#9ca3af' }}>
                  Continue to transcript
                </span>
              </Button>
            </div>
          </div>
        </Col>

        <Col xs={24} lg={8}>
          <div
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: 12,
              padding: '18px 20px',
              background: '#ffffff',
              height: '100%',
            }}
          >
            <Space align="start" size={10}>
              <InfoCircleOutlined style={{ color: '#4b5563', marginTop: 3 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#111827', marginBottom: 4 }}>
                  Audio upload ? published
                </div>
                <div style={{ fontSize: 12, color: '#6b7280', lineHeight: 1.55 }}>
                  Previewing confirms local audio playback and duration. Timestamped transcript attachment and admin approval are required before tour guides can play this narration.
                </div>
              </div>
            </Space>
          </div>
        </Col>
      </Row>
    </div>
  );
}
