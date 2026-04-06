FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV APP_ENV=production
ENV API_PREFIX=/api
ENV CORS_ORIGINS=["https://apetelin92.github.io"]
ENV STORAGE_ROOT=/tmp/vocal-storage
ENV FFMPEG_BIN=ffmpeg
ENV FFPROBE_BIN=ffprobe
ENV DEMUCS_COMMAND=demucs
ENV FLUIDSYNTH_BIN=fluidsynth
ENV SOME_ENABLED=false
ENV SOUNDFONT_PATH=/usr/share/sounds/sf2/FluidR3_GM.sf2

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        fluidsynth \
        fluid-soundfont-gm \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY backend /app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
