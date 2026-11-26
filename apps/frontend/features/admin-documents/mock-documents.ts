export type ReviewStatus = "Draft" | "Pending review" | "Approved" | "Changes requested";
export type IngestionStatus = "Not run" | "Indexed" | "Processing" | "Failed";
export interface DocumentRecord {
  id: string;
  filename: string;
  folder: string;
  size: number;
  format: string;
  title: string;
  region: string;
  documentType: string;
  sourceUrl: string;
  review: ReviewStatus;
  ingestion: IngestionStatus;
  uploader: string;
  updated: string;
  revision: number;
  file?: File;
}

const initial: DocumentRecord[] = [
  { id: "hue", filename: "Hue monument inventory.pdf", folder: "Vietnam / Central", size: 3355443, format: "PDF", title: "Hue monument inventory", region: "Central Vietnam", documentType: "Inventory", sourceUrl: "https://example.com/demo/hue", review: "Pending review", ingestion: "Not run", uploader: "Linh Tran", updated: "20 Oct, 08:50", revision: 1 },
  { id: "cham", filename: "Cham tower field notes.docx", folder: "Vietnam / Central", size: 860160, format: "DOCX", title: "Cham tower field notes", region: "Central Vietnam", documentType: "Field notes", sourceUrl: "https://example.com/demo/cham", review: "Pending review", ingestion: "Not run", uploader: "Mai Nguyen", updated: "20 Oct, 08:40", revision: 1 },
  { id: "coastal", filename: "Coastal archive index.docx", folder: "Drafts", size: 129024, format: "DOCX", title: "Coastal archive index", region: "Southern Vietnam", documentType: "Archive index", sourceUrl: "https://example.com/demo/coastal-archive-index", review: "Draft", ingestion: "Not run", uploader: "Mai Nguyen", updated: "20 Oct, 08:15", revision: 1 },
  { id: "hoian", filename: "Hoi An conservation guide.pdf", folder: "Vietnam / Central", size: 2516582, format: "PDF", title: "Hoi An conservation guide", region: "Central Vietnam", documentType: "Guide", sourceUrl: "https://example.com/demo/hoi-an", review: "Approved", ingestion: "Indexed", uploader: "Mai Nguyen", updated: "19 Oct, 10:12", revision: 1 },
  { id: "river", filename: "Red River oral histories.pdf", folder: "Vietnam / Northern", size: 9017754, format: "PDF", title: "Red River oral histories", region: "Northern Vietnam", documentType: "Oral history", sourceUrl: "https://example.com/demo/red-river", review: "Approved", ingestion: "Processing", uploader: "Linh Tran", updated: "19 Oct, 16:40", revision: 1 },
  { id: "mekong", filename: "Mekong craft survey.pdf", folder: "Vietnam / Southern", size: 5033165, format: "PDF", title: "Mekong craft survey", region: "Southern Vietnam", documentType: "Survey report", sourceUrl: "https://example.com/demo/mekong-craft-survey", review: "Approved", ingestion: "Failed", uploader: "Mai Nguyen", updated: "19 Oct, 14:10", revision: 1 },
  { id: "temple", filename: "Temple photo register.csv", folder: "Vietnam / Southern", size: 223232, format: "CSV", title: "Temple photo register", region: "Southern Vietnam", documentType: "Archive index", sourceUrl: "https://example.com/demo/temple", review: "Changes requested", ingestion: "Not run", uploader: "Linh Tran", updated: "19 Oct, 13:00", revision: 1 },
];

let records = initial.map((record) => ({ ...record }));
const listeners = new Set<() => void>();
export function getDocuments() { return records; }
export function subscribeDocuments(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; }
export function updateDocument(id: string, patch: Partial<DocumentRecord>) {
  records = records.map((record) => record.id === id ? { ...record, ...patch, id: record.id } : record);
  listeners.forEach((listener) => listener());
}
export function addDocument(file: File, folder: string) {
  const id = crypto.randomUUID();
  const record: DocumentRecord = { id, filename: file.name, folder, size: file.size, format: file.name.split(".").pop()?.toUpperCase() ?? "", title: file.name.replace(/\.[^.]+$/, ""), region: "", documentType: "", sourceUrl: "", review: "Draft", ingestion: "Not run", uploader: "Demo user", updated: "Just now", revision: 1, file };
  records = [record, ...records]; listeners.forEach((listener) => listener()); return id;
}
export function resetDocuments() { records = initial.map((record) => ({ ...record })); listeners.forEach((listener) => listener()); }
