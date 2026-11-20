import { KnowledgeProvider } from "@/features/knowledge/KnowledgeProvider";

export default function DocumentLibraryLayout({ children }: { children: React.ReactNode }) {
  return <KnowledgeProvider>{children}</KnowledgeProvider>;
}
