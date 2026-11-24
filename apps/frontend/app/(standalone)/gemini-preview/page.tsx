import type { Metadata } from 'next';
import GeminiChatClone from '@/features/gemini-preview/components/GeminiChatClone';

export const metadata: Metadata = {
  title: 'Gemini Chrome :: Cuộc trò chuyện mới',
  description: '1:1 Side Panel UI clone from gemini.html',
};

export default function GeminiPreviewPage() {
  return <GeminiChatClone />;
}
