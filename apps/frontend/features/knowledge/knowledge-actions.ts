import { ApiError } from "../../lib/api";
import { knowledgeApi } from "../../services/knowledge.service";

/** Open a tab during the click gesture; never add backend auth to its R2 URL. */
export async function downloadKnowledgeFile(key: string): Promise<void> {
  const target = window.open("about:blank", "_blank");
  if (target) target.opener = null;
  try {
    const result = await knowledgeApi.download(key);
    const url = new URL(result.downloadUrl);
    if (url.protocol !== "https:" || url.username || url.password) throw new ApiError("The backend returned an invalid download URL.", 503);
    if (target) target.location.replace(result.downloadUrl);
    else window.location.assign(result.downloadUrl);
  } catch (error) { target?.close(); throw error; }
}
