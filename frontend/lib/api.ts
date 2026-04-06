export type JobStatus =
  | "uploaded"
  | "validating"
  | "preprocessing"
  | "separating"
  | "transcribing"
  | "cleaning_midi"
  | "rendering_keys"
  | "mixing_preview"
  | "completed"
  | "failed";

export type JobEvent = {
  status: JobStatus;
  timestamp: string;
  message: string | null;
};

export type JobResponse = {
  job_id: string;
  status: JobStatus;
  original_filename: string;
  duration_seconds: number | null;
  transcription_engine: string | null;
  render_preset: string;
  error_message: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  events: JobEvent[];
};

export type RenderPresetOption = {
  id: string;
  label: string;
  description: string;
};

export type JobFile = {
  filename: string;
  kind: "audio" | "midi";
  content_type: string;
  download_url: string;
  preview_url: string | null;
  exists: boolean;
};

export type JobFilesResponse = {
  job_id: string;
  status: JobStatus;
  files: JobFile[];
};

export const API_CONFIGURATION_ERROR =
  "Set NEXT_PUBLIC_API_BASE_URL to a public backend URL to enable uploads on the deployed site.";

const ENV_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";
const DEFAULT_PRODUCTION_API_BASE_URL = "https://vocal-api-apetelin92.onrender.com";

function resolveApiBaseUrl(): string {
  if (ENV_API_BASE_URL) {
    return ENV_API_BASE_URL;
  }

  if (typeof window === "undefined") {
    return "";
  }

  return ["localhost", "127.0.0.1"].includes(window.location.hostname)
    ? "http://127.0.0.1:8000"
    : DEFAULT_PRODUCTION_API_BASE_URL;
}

export function hasApiBaseUrl(): boolean {
  return Boolean(resolveApiBaseUrl());
}

export function apiUrl(path: string): string {
  const apiBaseUrl = resolveApiBaseUrl();
  if (!apiBaseUrl) {
    throw new Error(API_CONFIGURATION_ERROR);
  }
  return `${apiBaseUrl}${path}`;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return response.json() as Promise<T>;
  }

  let message = "Request failed.";
  try {
    const payload = (await response.json()) as { detail?: string };
    message = payload.detail ?? message;
  } catch {
    message = response.statusText || message;
  }
  throw new Error(message);
}

export async function uploadSong(file: File): Promise<JobResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("render_preset", "acoustic_lead");
  const response = await fetch(apiUrl("/api/jobs/upload"), {
    method: "POST",
    body: form,
  });
  return handleResponse<JobResponse>(response);
}

export async function uploadSongWithPreset(file: File, renderPreset: string): Promise<JobResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("render_preset", renderPreset);
  const response = await fetch(apiUrl("/api/jobs/upload"), {
    method: "POST",
    body: form,
  });
  return handleResponse<JobResponse>(response);
}

export async function startJob(jobId: string): Promise<JobResponse> {
  const response = await fetch(apiUrl(`/api/jobs/${jobId}/start`), {
    method: "POST",
  });
  return handleResponse<JobResponse>(response);
}

export async function getJob(jobId: string): Promise<JobResponse> {
  const response = await fetch(apiUrl(`/api/jobs/${jobId}`), {
    cache: "no-store",
  });
  return handleResponse<JobResponse>(response);
}

export async function getJobFiles(jobId: string): Promise<JobFilesResponse> {
  const response = await fetch(apiUrl(`/api/jobs/${jobId}/files`), {
    cache: "no-store",
  });
  return handleResponse<JobFilesResponse>(response);
}

export async function getRenderPresets(): Promise<RenderPresetOption[]> {
  const response = await fetch(apiUrl("/api/render-presets"), {
    cache: "no-store",
  });
  return handleResponse<RenderPresetOption[]>(response);
}
