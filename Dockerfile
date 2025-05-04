FROM python:3.13-alpine

LABEL org.opencontainers.image.title="Video Archiver ZIM"
LABEL org.opencontainers.image.description="A tool to download videos from various platforms and create ZIM archives"
LABEL org.opencontainers.image.source="https://github.com/Sudo-Ivan/video-archiver-zim"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.authors="Sudo-Ivan"

WORKDIR /app

RUN apk add --no-cache \
    ffmpeg

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY archiver /app/archiver/

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/archive/media /app/archive/metadata /app/config /app/cookies

ENTRYPOINT ["python", "-m", "archiver.cli"]
CMD ["manage"]