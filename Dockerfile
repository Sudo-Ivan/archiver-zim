FROM python:3.13-alpine

LABEL org.opencontainers.image.title="Archiver ZIM"
LABEL org.opencontainers.image.description="A tool to download videos from various platforms and create ZIM archives"
LABEL org.opencontainers.image.source="https://github.com/Sudo-Ivan/archiver-zim"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.authors="Sudo-Ivan"

WORKDIR /app

RUN apk add --no-cache \
    ffmpeg

RUN pip install poetry
ENV PATH="/root/.poetry/bin:$PATH"

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root --no-interaction

COPY archiver_zim /app/archiver/

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/archive/media /app/archive/metadata /app/config /app/cookies

ENTRYPOINT ["python", "-m", "archiver.cli"]
CMD ["manage"]
