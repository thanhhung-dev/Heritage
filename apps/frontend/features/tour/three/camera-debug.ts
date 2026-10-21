/**
 * Log chẩn đoán camera cho tour 3D.
 *
 * Mặc định BẬT ở môi trường dev (`npm run dev`) và TẮT ở production.
 * - Tắt:  window.__tourCameraDebug = false
 * - Bật:  window.__tourCameraDebug = true
 * - Dump trạng thái bất kỳ lúc nào: window.__tourCameraDump()
 */

type DebugWindow = {
  __tourCameraDebug?: boolean;
  __tourCameraDump?: () => unknown;
};

export function cameraDebugEnabled() {
  if (typeof window === "undefined") return false;
  const flag = (window as unknown as DebugWindow).__tourCameraDebug;
  if (flag === false) return false;
  if (flag === true) return true;
  return process.env.NODE_ENV !== "production";
}

export function fmtVec(v: { x: number; y: number; z: number } | null | undefined) {
  if (!v) return "null";
  return `(${v.x.toFixed(2)}, ${v.y.toFixed(2)}, ${v.z.toFixed(2)})`;
}

const TAG_STYLE = "color:#185FA5;font-weight:600";
const WARN_STYLE = "color:#A32D2D;font-weight:600";

export function camLog(tag: string, message: string, data?: unknown) {
  if (!cameraDebugEnabled()) return;
  if (data === undefined) console.log(`%c[cam:${tag}]%c ${message}`, TAG_STYLE, "");
  else console.log(`%c[cam:${tag}]%c ${message}`, TAG_STYLE, "", data);
}

export function camWarn(tag: string, message: string, data?: unknown) {
  if (!cameraDebugEnabled()) return;
  if (data === undefined) console.warn(`%c[cam:${tag}]%c ${message}`, WARN_STYLE, "");
  else console.warn(`%c[cam:${tag}]%c ${message}`, WARN_STYLE, "", data);
}
