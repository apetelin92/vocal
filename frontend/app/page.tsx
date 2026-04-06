"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";

import {
  API_CONFIGURATION_ERROR,
  JobFile,
  JobResponse,
  JobStatus,
  RenderPresetOption,
  apiUrl,
  getJob,
  getJobFiles,
  getRenderPresets,
  hasApiBaseUrl,
  startJob,
  uploadSongWithPreset,
} from "../lib/api";

const INPUT_ACCEPT = ".mp3,.wav,.m4a,audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/m4a";
const TERMINAL_STATUSES: JobStatus[] = ["completed", "failed"];
const STATUS_LABELS: Record<JobStatus, string> = {
  uploaded: "Uploaded",
  validating: "Validating",
  preprocessing: "Preprocessing",
  separating: "Separating",
  transcribing: "Transcribing",
  cleaning_midi: "Cleaning MIDI",
  rendering_keys: "Rendering keys",
  mixing_preview: "Mixing preview",
  completed: "Completed",
  failed: "Failed",
};

const STATUS_PROGRESS: Record<JobStatus, number> = {
  uploaded: 6,
  validating: 14,
  preprocessing: 28,
  separating: 48,
  transcribing: 68,
  cleaning_midi: 78,
  rendering_keys: 88,
  mixing_preview: 96,
  completed: 100,
  failed: 0,
};

const FALLBACK_PRESETS: RenderPresetOption[] = [
  {
    id: "acoustic_lead",
    label: "Acoustic Lead",
    description: "Soft flute-like lead that is easier to sing against than the current piano soundfont.",
  },
  {
    id: "acoustic_piano",
    label: "Classic Piano",
    description: "Clean grand piano, best default for melody doubling and vocal guide playback.",
  },
  {
    id: "bright_piano",
    label: "Bright Piano",
    description: "Sharper attack that cuts through a dense accompaniment.",
  },
  {
    id: "electric_piano",
    label: "Electric Piano",
    description: "Softer electric keys tone for pop and lo-fi tracks.",
  },
  {
    id: "organ",
    label: "Organ",
    description: "Sustained organ lead for long vocal lines.",
  },
  {
    id: "strings",
    label: "Strings",
    description: "Light string layer for a smoother melodic guide.",
  },
  {
    id: "synth_lead",
    label: "Synth Lead",
    description: "Synthetic lead tone for a more obvious top melody.",
  },
];

function getPresetLabel(renderPreset: string, presets: RenderPresetOption[]): string {
  return presets.find((preset) => preset.id === renderPreset)?.label ?? renderPreset;
}

function getJobProgress(job: JobResponse | null): number {
  if (!job) {
    return 0;
  }
  if (job.status !== "failed") {
    return STATUS_PROGRESS[job.status];
  }
  const lastSuccessfulStage = [...job.events]
    .reverse()
    .find((event) => event.status !== "failed");
  return lastSuccessfulStage ? STATUS_PROGRESS[lastSuccessfulStage.status] : 0;
}

export default function HomePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [apiConfigured, setApiConfigured] = useState(false);
  const [renderPresets, setRenderPresets] = useState<RenderPresetOption[]>(FALLBACK_PRESETS);
  const [selectedRenderPreset, setSelectedRenderPreset] = useState<string>(FALLBACK_PRESETS[0].id);
  const [job, setJob] = useState<JobResponse | null>(null);
  const [files, setFiles] = useState<JobFile[]>([]);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const pollRef = useRef<number | null>(null);

  const canSubmit = Boolean(selectedFile) && !isSubmitting && apiConfigured;
  const isProcessing = job ? !TERMINAL_STATUSES.includes(job.status) : false;
  const visibleFiles = files.filter((file) => file.exists);
  const progress = getJobProgress(job);

  useEffect(() => {
    setApiConfigured(hasApiBaseUrl());
  }, []);

  useEffect(() => {
    if (!apiConfigured) {
      setRenderPresets(FALLBACK_PRESETS);
      return;
    }

    let cancelled = false;

    getRenderPresets()
      .then((presets) => {
        if (cancelled || !presets.length) {
          return;
        }
        setRenderPresets(presets);
        setSelectedRenderPreset((current) =>
          presets.some((preset) => preset.id === current) ? current : presets[0].id
        );
      })
      .catch(() => {
        if (!cancelled) {
          setRenderPresets(FALLBACK_PRESETS);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [apiConfigured]);

  useEffect(() => {
    if (!job || TERMINAL_STATUSES.includes(job.status)) {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }

    pollRef.current = window.setInterval(async () => {
      try {
        const nextJob = await getJob(job.job_id);
        setJob(nextJob);
        if (nextJob.status === "completed") {
          const result = await getJobFiles(nextJob.job_id);
          setFiles(result.files);
        }
      } catch (error) {
        setRequestError(error instanceof Error ? error.message : "Polling failed.");
      }
    }, 2000);

    return () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [job]);

  async function handleSubmit() {
    if (!apiConfigured) {
      setRequestError(API_CONFIGURATION_ERROR);
      return;
    }

    if (!selectedFile) {
      setRequestError("Choose one audio file before starting.");
      return;
    }

    setIsSubmitting(true);
    setRequestError(null);
    setFiles([]);

    try {
      const uploaded = await uploadSongWithPreset(selectedFile, selectedRenderPreset);
      setJob(uploaded);

      const started = await startJob(uploaded.job_id);
      setJob(started);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setSelectedFile(nextFile);
    setRequestError(null);
    setJob(null);
    setFiles([]);
  }

  return (
    <main className="page-shell">
      <section className="hero-card reveal">
        <div className="hero-copy">
          <span className="eyebrow">Local MVP</span>
          <h1>Vocal2Keys + Minus</h1>
          <p>
            Upload a full song and get separate vocals, accompaniment, melody MIDI,
            rendered piano keys, and a quick preview mix.
          </p>
        </div>

        <div className="upload-card">
          <label className="upload-dropzone" htmlFor="audio-upload">
            <span>Song file</span>
            <strong>{selectedFile ? selectedFile.name : "Drop or choose mp3, wav, m4a"}</strong>
            <small>One file per job, up to 10 minutes.</small>
          </label>
          <input id="audio-upload" type="file" accept={INPUT_ACCEPT} onChange={onFileChange} />

          <label className="select-field">
            <span>Keys sound</span>
            <select
              value={selectedRenderPreset}
              disabled={!apiConfigured}
              onChange={(event) => setSelectedRenderPreset(event.target.value)}
            >
              {renderPresets.map((preset) => (
                <option key={preset.id} value={preset.id}>
                  {preset.label}
                </option>
              ))}
            </select>
            <small>
              {renderPresets.find((preset) => preset.id === selectedRenderPreset)?.description ??
                "Choose how the rendered melody should sound in keys.wav and preview_mix.wav."}
            </small>
          </label>

          <button className="primary-button" onClick={handleSubmit} disabled={!canSubmit}>
            {isSubmitting ? "Uploading..." : "Upload and Start"}
          </button>

          {!apiConfigured ? <p className="notice-banner">{API_CONFIGURATION_ERROR}</p> : null}
          {requestError ? <p className="error-banner">{requestError}</p> : null}
        </div>
      </section>

      <section className="content-grid">
        <div className="panel reveal">
          <div className="panel-header">
            <h2>Job Status</h2>
            <span className={`status-pill status-${job?.status ?? "uploaded"}`}>
              {job ? STATUS_LABELS[job.status] : "Waiting"}
            </span>
          </div>

          {job ? (
            <>
              <dl className="job-meta">
                <div>
                  <dt>Job ID</dt>
                  <dd>{job.job_id}</dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{job.original_filename}</dd>
                </div>
                <div>
                  <dt>Duration</dt>
                  <dd>{job.duration_seconds ? `${job.duration_seconds.toFixed(1)} sec` : "Pending"}</dd>
                </div>
                <div>
                  <dt>Engine</dt>
                  <dd>{job.transcription_engine ?? "Pending"}</dd>
                </div>
                <div>
                  <dt>Keys sound</dt>
                  <dd>{getPresetLabel(job.render_preset, renderPresets)}</dd>
                </div>
              </dl>

              <div className="progress-block" aria-live="polite">
                <div className="progress-label-row">
                  <strong>Pipeline Progress</strong>
                  <span>{progress}%</span>
                </div>
                <div className={`progress-track ${job?.status === "failed" ? "progress-failed" : ""}`}>
                  <div className="progress-fill" style={{ width: `${progress}%` }} />
                </div>
              </div>

              <div className="timeline">
                {job.events.map((event, index) => (
                  <div className="timeline-item" key={`${event.timestamp}-${index}`}>
                    <div className="timeline-dot" />
                    <div>
                      <strong>{STATUS_LABELS[event.status]}</strong>
                      <p>{event.message ?? "No extra details."}</p>
                    </div>
                  </div>
                ))}
              </div>

              {job.status === "failed" ? (
                <div className="failure-card">
                  <strong>{job.failure_reason ?? "Job failed."}</strong>
                  <p>{job.error_message ?? "No extra error details available."}</p>
                </div>
              ) : null}

              {isProcessing ? <p className="hint-text">Polling backend every 2 seconds.</p> : null}
            </>
          ) : (
            <p className="empty-state">Upload a song to create a job and track its processing steps.</p>
          )}
        </div>

        <div className="panel reveal delay">
          <div className="panel-header">
            <h2>Outputs</h2>
            <span className="panel-note">{visibleFiles.length ? `${visibleFiles.length} files` : "No files yet"}</span>
          </div>

          {visibleFiles.length ? (
            <div className="outputs-grid">
              {visibleFiles.map((file) => {
                const absoluteDownload = apiConfigured ? apiUrl(file.download_url) : "#";
                return (
                  <article className="output-card" key={file.filename}>
                    <div>
                      <span className="output-kind">{file.kind}</span>
                      <h3>{file.filename}</h3>
                    </div>

                    {file.preview_url ? (
                      <audio
                        controls
                        preload="none"
                        src={apiConfigured ? apiUrl(file.preview_url) : undefined}
                      >
                        Your browser does not support audio preview.
                      </audio>
                    ) : (
                      <p className="hint-text">Preview is available for audio outputs only.</p>
                    )}

                    <a className="secondary-button" href={absoluteDownload} target="_blank" rel="noreferrer">
                      Download
                    </a>
                  </article>
                );
              })}
            </div>
          ) : (
            <p className="empty-state">
              Completed jobs will show <code>vocals.wav</code>, <code>accompaniment.wav</code>,{" "}
              <code>melody.mid</code>, <code>keys.wav</code>, and <code>preview_mix.wav</code>.
            </p>
          )}
        </div>
      </section>
    </main>
  );
}
