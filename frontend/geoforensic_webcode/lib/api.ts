export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

type HttpMethod = "GET" | "POST";

async function fetchApi<T>(path: string, options?: { method?: HttpMethod; body?: unknown; token?: string }): Promise<T> {
  const method = options?.method ?? "GET";
  const token = options?.token ?? (typeof window !== "undefined" ? localStorage.getItem("gf_token") ?? undefined : undefined);
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options?.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `Request failed with status ${response.status}`;
    throw new ApiError(detail, response.status, payload);
  }

  return payload as T;
}

export type User = {
  id: string;
  email: string;
  company_name?: string | null;
  gutachter_type?: string | null;
  created_at?: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: User;
};

export type PreviewResponse = {
  ampel: "gruen" | "gelb" | "rot" | null;
  point_count: number;
  address_resolved: string;
  latitude: number;
  longitude: number;
};

export type ReportListItem = {
  id: string;
  address_input: string;
  status: "processing" | "completed" | "failed";
  ampel: "gruen" | "gelb" | "rot" | null;
  paid: boolean;
  geo_score: number | null;
  created_at: string;
};

export type ReportDetail = ReportListItem & {
  latitude: number;
  longitude: number;
  radius_m: number;
  aktenzeichen: string | null;
  report_data: Record<string, unknown> | null;
  pdf_available: boolean;
};

export async function register(body: {
  email: string;
  password: string;
  company_name?: string;
  gutachter_type?: string;
}): Promise<AuthResponse> {
  return fetchApi<AuthResponse>("/api/auth/register", { method: "POST", body });
}

export async function login(body: { email: string; password: string }): Promise<AuthResponse> {
  return fetchApi<AuthResponse>("/api/auth/login", { method: "POST", body });
}

export async function getMe(token?: string): Promise<User> {
  return fetchApi<User>("/api/auth/me", { token });
}

export async function previewReport(body: { address: string }): Promise<PreviewResponse> {
  return fetchApi<PreviewResponse>("/api/reports/preview", { method: "POST", body });
}

export async function createReport(
  body: { address: string; radius_m: number; aktenzeichen?: string; selected_modules?: string[] },
  token?: string
): Promise<ReportDetail> {
  return fetchApi<ReportDetail>("/api/reports/create", { method: "POST", body, token });
}

export async function getReports(token?: string): Promise<ReportListItem[]> {
  return fetchApi<ReportListItem[]>("/api/reports", { token });
}

export async function getReport(id: string, token?: string): Promise<ReportDetail> {
  return fetchApi<ReportDetail>(`/api/reports/${id}`, { token });
}

export async function checkout(reportId: string, token?: string): Promise<{ checkout_url: string }> {
  return fetchApi<{ checkout_url: string }>("/api/payments/checkout", {
    method: "POST",
    body: { report_id: reportId },
    token,
  });
}

