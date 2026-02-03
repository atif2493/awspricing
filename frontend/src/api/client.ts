/**
 * API client for awspricing backend.
 * Port: 8000 (backend). Deps: none.
 */

const API_BASE = "";

export type AwsBackupPricing = {
  rate_per_gb_month: number | null;
  currency?: string;
  unit?: string;
  sku?: string;
  product_attributes?: Record<string, string>;
  term_code?: string;
  price_dimension?: Record<string, unknown>;
  raw_filter?: Record<string, unknown>;
  error?: string;
  cached_at?: number;
  from_cache?: boolean;
};

export type S3StoragePricing = {
  rate_per_gb_month?: number | null;
  tiers?: Array<{ from_gb: number; to_gb: number; rate_per_gb_month: number }>;
  currency?: string;
  unit?: string;
  sku?: string;
  product_attributes?: Record<string, string>;
  term_code?: string;
  price_dimension?: Record<string, unknown>;
  raw_filter?: Record<string, unknown>;
  error?: string;
  cached_at?: number;
  from_cache?: boolean;
};

export type RegionOption = { code: string; location: string };

export async function fetchAwsBackupPricing(
  region: string,
  currency: string,
  refresh = false
): Promise<AwsBackupPricing> {
  const params = new URLSearchParams({ region, currency });
  if (refresh) params.set("refresh", "true");
  const res = await fetch(`${API_BASE}/api/pricing/aws-backup?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchS3StoragePricing(
  region: string,
  currency: string,
  storageClass: string,
  refresh = false
): Promise<S3StoragePricing> {
  const params = new URLSearchParams({ region, currency, storageClass });
  if (refresh) params.set("refresh", "true");
  const res = await fetch(`${API_BASE}/api/pricing/s3-storage?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchRegions(): Promise<RegionOption[]> {
  const res = await fetch(`${API_BASE}/api/regions`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// --- Conversation (AI multi-cloud calculator) ---

export type ConversationMode = "expert" | "balanced" | "guided";

export type ConversationRequest = {
  session_id?: string | null;
  message: string;
  mode?: ConversationMode;
  image?: string | null; // base64
  image_media_type?: string | null; // e.g. image/png, image/jpeg
};

export type ConversationResponse = {
  reply: string;
  session_id: string;
  recommendation: unknown;
};

export async function postConversation(
  body: ConversationRequest
): Promise<ConversationResponse> {
  const res = await fetch(`${API_BASE}/api/conversation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: body.session_id ?? null,
      message: body.message,
      mode: body.mode ?? "balanced",
      image: body.image ?? null,
      image_media_type: body.image_media_type ?? null,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export type SessionResponse = {
  session_id: string;
  mode: ConversationMode;
};

export async function postSession(body: {
  session_id?: string | null;
  mode?: ConversationMode;
}): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: body.session_id ?? null,
      mode: body.mode ?? "balanced",
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getSessionInfo(
  sessionId: string
): Promise<{ session_id: string; mode: ConversationMode; message_count: number }> {
  const res = await fetch(`${API_BASE}/api/session/${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
