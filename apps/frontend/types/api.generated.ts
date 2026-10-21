// Generated from the FastAPI OpenAPI contract. Do not edit by hand.
// Regenerate with `npm run api:generate` from apps/frontend.

export interface components {
  schemas: {
      "ChatErrorResponse": {
    "detail": string | Record<string, unknown>;
  };
      "ChatRequest": {
    "message": string;
    "use_rag"?: boolean;
    "session_id"?: string | null;
  };
      "ChatResponse": {
    "answer": string;
    "sources"?: Array<components["schemas"]["ChatSource"]>;
    "corrected_from"?: string;
    "corrected_to"?: string;
    "needs_user_choice"?: boolean;
    "suggestions"?: Array<components["schemas"]["EntitySuggestion"] | components["schemas"]["CorrectionSuggestion"]>;
    "entity_id"?: string | null;
    "intent"?: string | null;
    "resolution_status"?: string | null;
    "answer_type"?: string | null;
  };
      "ChatSource": {
    "text"?: string | null;
    "score"?: number | null;
    "doc"?: string | null;
    "heading"?: string | null;
    "url"?: string | null;
    "chunk_id"?: string | null;
    "graph"?: number | null;
    "graph_hits"?: Array<string> | null;
    "used_in_context"?: boolean | null;
    "passage_id"?: string | null;
    "quote"?: string | null;
  };
      "CorrectionSuggestion": {
    "original": string;
    "suggested": string;
    "score": number;
  };
      "EntitySource": {
    "document_id": string;
  };
      "EntitySuggestion": {
    "entity_id": string;
    "canonical_name": string;
    "normalized_name": string;
    "type": string;
    "alias_used": string | null;
    "score": number;
    "sources": Array<components["schemas"]["EntitySource"]>;
  };
      "HTTPValidationError": {
    "detail"?: Array<components["schemas"]["ValidationError"]>;
  };
      "TourResponse": {
    "slug": string;
    "locale": string;
    "title": string;
    "tagline"?: string | null;
    "location_label"?: string | null;
    "splash_image_url"?: string | null;
    "ambient_audio_url"?: string | null;
    "default_camera_clip_url"?: string | null;
    "revision": number;
    "published_at"?: string | null;
    "stops"?: Array<components["schemas"]["TourStopResponse"]>;
  };
      "TourStopResponse": {
    "story_id": string;
    "order_index": number;
    "title": string;
    "description"?: string | null;
    "scene_title"?: string | null;
    "scene_description"?: string | null;
    "bbox_min"?: string | null;
    "bbox_max"?: string | null;
    "transform_7dof"?: Record<string, unknown> | null;
    "model_url"?: string | null;
    "camera_clip_url"?: string | null;
    "camera_name"?: string | null;
    "clip_start_s"?: number | null;
    "clip_end_s"?: number | null;
    "camera_fov"?: number | null;
    "pan_enable"?: boolean;
    "instant_move"?: boolean;
    "sky"?: string | null;
    "free_explore"?: boolean;
    "explore_area"?: Record<string, unknown> | null;
    "start_camera_position"?: string | null;
    "start_camera_target"?: string | null;
    "zoom_camera_position"?: string | null;
    "zoom_camera_target"?: string | null;
    "narration_url"?: string | null;
    "captions_vtt_url"?: string | null;
    "narration_duration_ms"?: number | null;
    "highlights"?: Array<Record<string, unknown>>;
  };
      "ValidationError": {
    "loc": Array<string | number>;
    "msg": string;
    "type": string;
    "input"?: unknown;
    "ctx"?: Record<string, unknown>;
  };
  };
}

export interface paths {
  "/api/health": {
    get:   {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
      };
  };
  "/api/chat": {
    post:   {
      requestBody: { required: true; content: { "application/json": components["schemas"]["ChatRequest"] } };
      responses: {
        "200": { content: { "application/json": components["schemas"]["ChatResponse"] } };
        "400": { content: { "application/json": components["schemas"]["ChatErrorResponse"] } };
        "500": { content: { "application/json": components["schemas"]["ChatErrorResponse"] } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
      };
  };
  "/api/graph/stats": {
    get:   {
      responses: {
        "200": { content: { "application/json": Record<string, unknown> } };
      };
      };
  };
  "/api/graph/subgraph": {
    get:   {
      parameters: {
        "query": {
          "node": string;
          "hops"?: number;
        };
      };
      responses: {
        "200": { content: { "application/json": Record<string, unknown> } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
      };
  };
  "/api/graph/trace": {
    get:   {
      parameters: {
        "query": {
          "q": string;
          "top_k"?: number;
        };
      };
      responses: {
        "200": { content: { "application/json": Record<string, unknown> } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
      };
  };
  "/api/tours/{slug}": {
    get:   {
      parameters: {
        "path": {
          "slug": string;
        };
        "query"?: {
          "locale"?: string;
        };
      };
      responses: {
        "200": { content: { "application/json": components["schemas"]["TourResponse"] } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
      };
  };
  "/": {
    get:   {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
      };
  };
}
