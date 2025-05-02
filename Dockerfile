FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY archiver.py .

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/archive/media /app/archive/metadata

ENTRYPOINT ["python", "archiver.py"]
CMD ["--help"] 