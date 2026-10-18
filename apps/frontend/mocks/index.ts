import type { components } from "@/types/api.generated";

type ChatRequest = components["schemas"]["ChatRequest"];
type ChatResponse = components["schemas"]["ChatResponse"];
type ApiErrorResponse = components["schemas"]["ChatErrorResponse"];
type ValidationErrorResponse = components["schemas"]["HTTPValidationError"];

const chatSuccess: ChatResponse = {
  answer:
    "Lăng Tự Đức là một quần thể lăng tẩm thời Nguyễn tại Huế. Hãy dùng nguồn đính kèm để tìm hiểu thêm.",
  sources: [
    {
      doc: "Lăng Tự Đức",
      heading: "Tổng quan",
      text: "Lăng Tự Đức là một công trình kiến trúc tiêu biểu của triều Nguyễn.",
      score: 0.94,
      chunk_id: "mock-tu-duc-01",
    },
  ],
  corrected_from: "",
  corrected_to: "",
  needs_user_choice: false,
  suggestions: [],
  entity_id: null,
  intent: null,
  resolution_status: "resolved",
  answer_type: "retrieval",
};

const chatEmpty: ChatResponse = {
  answer:
    "Tôi không tìm thấy nguồn phù hợp trong dữ liệu hiện có, nên chưa thể trả lời câu hỏi này mà không suy đoán.",
  sources: [],
  corrected_from: "",
  corrected_to: "",
  needs_user_choice: false,
  suggestions: [],
  entity_id: null,
  intent: null,
  resolution_status: "not_found",
  answer_type: "insufficient_evidence",
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function readChatRequest(body: BodyInit | null | undefined): ChatRequest | null {
  if (typeof body !== "string") return null;
  try {
    return JSON.parse(body) as ChatRequest;
  } catch {
    return null;
  }
}

/** Routes the same API paths as FastAPI while NEXT_PUBLIC_API_URL=mock. */
export async function requestMockApi(
  endpoint: string,
  options: RequestInit = {},
): Promise<Response> {
  await new Promise((resolve) => setTimeout(resolve, 180));

  const url = new URL(endpoint, "http://mock.local");
  const method = (options.method ?? "GET").toUpperCase();

  if (url.pathname === "/api/chat" && method === "POST") {
    const request = readChatRequest(options.body);
    if (!request) {
      const validationError: ValidationErrorResponse = {
        detail: [
          {
            loc: ["body"],
            msg: "Invalid JSON body",
            type: "json_invalid",
          },
        ],
      };
      return jsonResponse(validationError, 422);
    }

    if (typeof request.message !== "string") {
      const validationError: ValidationErrorResponse = {
        detail: [
          {
            loc: ["body", "message"],
            msg: "Field required",
            type: "missing",
          },
        ],
      };
      return jsonResponse(validationError, 422);
    }

    if (!request.message.trim()) {
      const error: ApiErrorResponse = { detail: "message trống" };
      return jsonResponse(error, 400);
    }

    if (request.message.includes("[mock:error]")) {
      const error: ApiErrorResponse = { detail: "Mock server error" };
      return jsonResponse(error, 500);
    }

    return jsonResponse(
      request.message.includes("[mock:empty]") ? chatEmpty : chatSuccess,
    );
  }

  const error: ApiErrorResponse = {
    detail: `Mock chưa cấu hình: ${method} ${url.pathname}`,
  };
  return jsonResponse(error, 404);
}
