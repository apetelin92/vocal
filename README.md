# Vocal2Keys + Minus

Local MVP web app that:

1. uploads one full song (`mp3`, `wav`, `m4a`)
2. validates duration (`<= 10 minutes`)
3. normalizes audio with `ffmpeg`
4. separates stems with `Demucs`
5. transcribes the vocal melody to MIDI
6. cleans the MIDI
7. renders a piano track from MIDI with `FluidSynth`
8. creates a preview mix (`accompaniment + keys`)
9. exposes downloadable files and job polling

## Stack

- `frontend/`: Next.js + TypeScript
- `backend/`: FastAPI + Python
- `storage/`: local job metadata and generated files

## Output Files

- `vocals.wav`
- `accompaniment.wav`
- `melody.mid`
- `keys.wav`
- `preview_mix.wav`

## API

- `POST /api/jobs/upload`
- `POST /api/jobs/{jobId}/start`
- `GET /api/jobs/{jobId}`
- `GET /api/jobs/{jobId}/files`
- `GET /api/download/{jobId}/{filename}`

## Job Statuses

- `uploaded`
- `validating`
- `preprocessing`
- `separating`
- `transcribing`
- `cleaning_midi`
- `rendering_keys`
- `mixing_preview`
- `completed`
- `failed`

## Project Structure

```text
apps/vocal
├── backend
│   ├── app
│   ├── tests
│   ├── requirements.txt
│   └── .env.example
├── frontend
│   ├── app
│   ├── lib
│   ├── package.json
│   └── .env.example
└── storage
```

## External Dependencies

Required system tools:

- `ffmpeg`
- `ffprobe`
- `fluidsynth`

Required Python packages:

- `fastapi`
- `uvicorn`
- `pretty_midi`
- `demucs`
- `basic-pitch`
- `python-multipart`
- `pydantic-settings`

Required runtime assets/setup:

- a General MIDI SoundFont `.sf2` file for `FluidSynth`
- official `OpenVPI/SOME` repo checkout plus a pretrained SOME checkpoint

## About SOME

The backend now integrates the real official `OpenVPI/SOME` repository and invokes its official CLI entrypoint:

```bash
python infer.py --model CKPT_PATH --wav WAV_PATH --midi MIDI_PATH
```

Runtime behavior:

- `SOME` is the primary transcription engine when `SOME_ENABLED=true`
- `Basic Pitch` remains the fallback if `SOME` is disabled, misconfigured, or inference fails
- `infer.py` requires `config.yaml` to sit next to the checkpoint file, because the script loads `model_path.with_name("config.yaml")`
- for better pitch extraction, the SOME README recommends downloading the RMVPE pretrained model and extracting it into `pretrained/` inside the SOME repo
- the frontend lets the user choose a `keys` sound preset before upload; the backend applies that preset during `keys.wav` and `preview_mix.wav` rendering

## macOS Setup

System tools:

```bash
brew install ffmpeg fluid-synth
```

Backend app environment:

```bash
cd /Users/apetelin/Workspace/apps/vocal/backend
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
cp .env.example .env
```

Official SOME environment:

```bash
cd /Users/apetelin/Workspace/apps/vocal
git clone https://github.com/openvpi/SOME.git external/SOME
/opt/homebrew/bin/python3.11 -m venv external/SOME/.venv
source external/SOME/.venv/bin/activate
```

Install PyTorch for SOME first, using the official PyTorch selector for your platform:

```bash
# Example only. Pick the exact command from https://pytorch.org/get-started/locally/
pip install torch torchaudio
```

Then install official SOME requirements:

```bash
cd /Users/apetelin/Workspace/apps/vocal/external/SOME
pip install --upgrade pip
pip install -r requirements.txt
```

If `pip install -r requirements.txt` fails on newer `pip` because of legacy `omegaconf` metadata validation, use:

```bash
pip install "pip<24.1"
pip install -r requirements.txt
```

Download SOME model weights from the official releases:

- `v1.0.0-baseline`: `0119_continuous128_5spk.zip`
- older `v0.0.1` assets also exist, but prefer the baseline release unless you have a reason not to

Extract the SOME model zip somewhere local, for example:

```text
/Users/apetelin/Workspace/apps/vocal/models/some/0119_continuous256_5spk/
```

Important:

- point `SOME_MODEL_PATH` to the actual `.ckpt` file inside the extracted model folder
- keep the `config.yaml` from that same zip in the same folder as the `.ckpt`
- the current baseline zip `0119_continuous128_5spk.zip` extracts to a folder named `0119_continuous256_5spk/`, so use the extracted path, not just the zip filename
- if you use RMVPE, download it from the official RMVPE releases and extract it into:

```text
/Users/apetelin/Workspace/apps/vocal/external/SOME/pretrained/
```

Frontend:

```bash
cd /Users/apetelin/Workspace/apps/vocal/frontend
npm install
cp .env.example .env.local
```

Quick backend validation:

```bash
cd /Users/apetelin/Workspace/apps/vocal/backend
source .venv/bin/activate
pytest
```

## Required Environment Variables

Backend `.env`:

- `STORAGE_ROOT=../storage`
- `SOUNDFONT_PATH=/absolute/path/to/your-piano-or-general-midi.sf2`
- `SOME_ENABLED=true` to enable SOME before Basic Pitch fallback
- `SOME_REPO_PATH=/Users/apetelin/Workspace/apps/vocal/external/SOME`
- `SOME_MODEL_PATH=/Users/apetelin/Workspace/apps/vocal/models/some/0119_continuous256_5spk/model_ckpt_steps_100000_simplified.ckpt`
- `SOME_PYTHON_BIN=/Users/apetelin/Workspace/apps/vocal/external/SOME/.venv/bin/python`

Frontend `.env.local`:

- `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`

## GitHub Pages Frontend

The repository now includes a GitHub Actions workflow at `.github/workflows/deploy-pages.yml`
that publishes the static Next.js frontend to GitHub Pages on every push to `main`.

Notes:

- only `frontend/` is deployed to Pages
- the FastAPI backend cannot run on GitHub Pages
- set the repository variable `NEXT_PUBLIC_API_BASE_URL` to your public backend URL before
  expecting uploads to work on the deployed site
- for a repository named `vocal`, the default Pages URL will be:

```text
https://apetelin92.github.io/vocal/
```

## Backend Hosting

For this project, a Docker-based host with persistent storage is the practical choice.
The backend depends on:

- `ffmpeg`
- `fluidsynth`
- local file storage for jobs and generated outputs
- CPU-heavy audio/ML processing (`demucs`, `basic-pitch`, optionally `SOME`)

Recommended deployment target:

- Railway with a mounted volume

The repo now includes:

- [backend/Dockerfile](/Users/apetelin/Workspace/apps/vocal/backend/Dockerfile)
- `GET /health` for platform health checks

Railway setup notes for this repo:

- connect the GitHub repo `apetelin92/vocal`
- keep the service source at the repository root
- set `RAILWAY_DOCKERFILE_PATH=backend/Dockerfile`
- do not change the root directory to `backend`, because the Dockerfile expects the repository root as build context

Suggested production environment variables for the backend service:

```text
APP_ENV=production
API_PREFIX=/api
CORS_ORIGINS=["https://apetelin92.github.io"]
STORAGE_ROOT=/data/storage
SOME_ENABLED=false
FFMPEG_BIN=ffmpeg
FFPROBE_BIN=ffprobe
DEMUCS_COMMAND=demucs
FLUIDSYNTH_BIN=fluidsynth
SOUNDFONT_PATH=/data/assets/GeneralUser_GS.sf2
```

## Render Deployment

The backend is now configured so Render can boot it without manual environment setup.
The Docker image bakes in these production defaults:

- `APP_ENV=production`
- `API_PREFIX=/api`
- `CORS_ORIGINS=["https://apetelin92.github.io"]`
- `STORAGE_ROOT=/tmp/vocal-storage`
- `DEMUCS_MODEL=mdx_q`
- `SOME_ENABLED=false`
- `SOUNDFONT_PATH=/usr/share/sounds/sf2/FluidR3_GM.sf2`

That means a basic Render deployment only needs:

- repo `apetelin92/vocal`
- service type `Web Service`
- runtime `Docker`
- Dockerfile path `backend/Dockerfile`
- health check path `/health`

Notes:

- Render `Free` works for a demo, but its filesystem is ephemeral and the service spins down
- generated files under `/tmp/vocal-storage` can disappear after restart or redeploy
- if you need durable job artifacts, attach persistent storage on a paid plan and override
  `STORAGE_ROOT`

Notes:

- mount a persistent volume at `/data`
- the Docker image installs `fluid-soundfont-gm`, so the easiest default is:

```text
SOUNDFONT_PATH=/usr/share/sounds/sf2/FluidR3_GM.sf2
```

- use a custom SoundFont only if you want a different timbre
- if you later enable `SOME`, you will also need to place the official SOME repo and model files on persistent storage and set `SOME_REPO_PATH`, `SOME_MODEL_PATH`, and `SOME_PYTHON_BIN`
- after the backend gets a public URL, set the GitHub repository variable `NEXT_PUBLIC_API_BASE_URL` in the frontend repo and redeploy Pages

## Run Locally

Terminal 1:

```bash
cd /Users/apetelin/Workspace/apps/vocal/backend
source .venv/bin/activate
uvicorn app.main:app --reload --reload-dir app --reload-dir tests --port 8000
```

Terminal 2:

```bash
cd /Users/apetelin/Workspace/apps/vocal/frontend
npm run dev
```

## Keys Sound Presets

The MVP exposes a small set of General MIDI render presets through:

```text
GET /api/render-presets
```

Current built-in options:

- `acoustic_lead`
- `acoustic_piano`
- `bright_piano`
- `electric_piano`
- `organ`
- `strings`
- `synth_lead`

Upload requests can include the selected preset as multipart field:

```text
render_preset=acoustic_piano
```

If omitted, the backend uses `acoustic_piano`.
If omitted, the backend now uses `acoustic_lead`.

## Tuning Melody Accuracy

If the extracted MIDI melody does not resemble the original vocal closely enough, the most important controls are the cleanup and mix settings in backend `.env`:

- `MIDI_MIN_NOTE_MS=45`
  Lower this if short vocal notes, pickups, or ornaments disappear. Raise it if the MIDI is too noisy.
- `MIDI_MERGE_GAP_MS=20`
  Lower this if nearby notes are getting merged too aggressively. Raise it if the melody sounds too fragmented.
- `MIDI_QUANTIZE_MS=5`
  Lower this or set it to `0` to preserve more natural vocal timing. Raise it if the melody feels too jittery.
- `MIDI_OCTAVE_SNAP_ENABLED=true`
  Keeps the melody in a singable register by correcting obvious octave flips.
- `MIDI_OCTAVE_SNAP_JUMP_SEMITONES=8`
  If consecutive notes jump farther than this, the cleanup tries octave-shifting the new note to stay closer to the previous phrase.
- `MIDI_TARGET_PITCH_MIN=48`
- `MIDI_TARGET_PITCH_MAX=76`
  Preferred melodic range for the post-processed guide line.
- `PREVIEW_MIX_ACCOMPANIMENT_GAIN=0.72`
  Lowers the minus in `preview_mix.wav`.
- `PREVIEW_MIX_KEYS_GAIN=1.35`
  Pushes the rendered melody above the minus in `preview_mix.wav`.

Recommended starting point for your goal:

- use `Acoustic Lead` in the UI
- keep `SOME` enabled as primary engine
- if melody still feels too unlike the vocal, first try `MIDI_QUANTIZE_MS=0`
- if fast vocal turns are still missing, try `MIDI_MIN_NOTE_MS=30`

Open:

```text
http://127.0.0.1:3000
```

If port `3000` is already busy, Next.js may move to `3001` automatically:

```text
http://127.0.0.1:3001
```

## Notes On Replacing Local MVP Pieces Later

- `JobStore` is file-based and can be replaced with a DB or Redis-backed repository.
- `storage/` paths are stored as relative paths, which makes S3 migration easier later.
- transcription uses an adapter interface, so `SOME` and `Basic Pitch` are swappable.
- the worker queue is in-process today and can be replaced with Redis/Celery/RQ later.
- keyboard rendering is file-only via `FluidSynth`, so it does not need to play live audio during job processing

## Tests

Minimal backend tests cover:

- validation rules
- job state transitions
- upload API response shape

Run:

```bash
cd /Users/apetelin/Workspace/apps/vocal/backend
source .venv/bin/activate
pytest
```

## Limitations

- no auth
- no multi-user queue isolation
- no manual MIDI editor
- no harmony generation
- no persistent external worker
- SOME still requires you to install the official repo and provide a valid checkpoint path
- rendering requires you to provide a local `.sf2` SoundFont
- rendering requires you to provide a local `.sf2` SoundFont
