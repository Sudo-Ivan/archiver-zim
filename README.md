# Archiver ZIM

[![Socket Badge](https://socket.dev/api/badge/pypi/package/archiver-zim/0.2.1?artifact_id=tar-gz)](https://socket.dev/pypi/package/archiver-zim/overview/0.2.1/tar-gz)
[![DeepSource](https://app.deepsource.com/gh/Sudo-Ivan/archiver-zim.svg/?label=active+issues&show_trend=true&token=HQKcgToHNqsWxbY1_gs_Tc7h)](https://app.deepsource.com/gh/Sudo-Ivan/archiver-zim/)

A tool for downloading and archiving videos and podcasts into ZIM files.

## Features

- Continuous running mode for automatic updates
- Support for YouTube channels, playlists, and podcast feeds
- Configurable update frequencies
- Mixed content archives
- Automatic cleanup after archiving
- Rich progress tracking and logging
- Docker support for easy deployment

## Installation

Requires:

- Python 3.10+
- libzim
- ffmpeg

### Using Docker (Recommended)

1. Pull the Docker image:
```bash
docker pull ghcr.io/sudo-ivan/archiver-zim:latest
```

2. Create required directories:
```bash
mkdir -p archive/media archive/metadata config
```

3. Create a `config.yml` file in the config directory (see Configuration section below)

4. Run using Docker:
```bash
# Run in continuous mode
docker run -d \
  --name archiver-zim \
  -v $(pwd)/archive:/app/archive \
  -v $(pwd)/config:/app/config \
  -e TZ=UTC \
  ghcr.io/sudo-ivan/archiver-zim:latest manage

# Run single archive
docker run --rm \
  -v $(pwd)/archive:/app/archive \
  ghcr.io/sudo-ivan/archiver-zim:latest archive \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  --quality 720p \
  --title "My Video" \
  --description "My video collection"
```

### Using Docker Compose

1. Create a `docker-compose.yml` file:
```yaml
version: '3.8'

services:
  archiver:
    image: ghcr.io/sudo-ivan/archiver-zim:latest
    container_name: archiver-zim
    volumes:
      - ./archive:/app/archive
      - ./config:/app/config
    environment:
      - TZ=UTC
    restart: unless-stopped
    # Uncomment and modify the command as needed:
    # command: manage  # For continuous mode
    # command: archive "https://www.youtube.com/watch?v=VIDEO_ID" --quality 720p  # For single archive
```

2. Run using Docker Compose:
```bash
# Start in continuous mode
docker compose up -d

# Run single archive
docker compose run --rm archiver archive "https://www.youtube.com/watch?v=VIDEO_ID" --quality 720p

# View logs
docker compose logs -f
```

### Manual Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Install yt-dlp (required for video downloads):
```bash
pip install yt-dlp
```

### Using pip

Install directly from PyPI:
```bash
pip install archiver-zim
```

Install using pipx for isolated environment:
```bash
pipx install archiver-zim
```

## CLI

The tool provides a command-line interface with two main commands:

### Manage Command
```bash
archiver-zim manage [OPTIONS]
```

Options:
- `--config PATH`: Path to config file (default: ./config/config.yml)
- `--log-level LEVEL`: Set logging level (default: INFO)

### Archive Command
```bash
archiver-zim archive [URLS]... [OPTIONS]
```

Options:
- `--output-dir PATH`: Output directory for archives
- `--quality QUALITY`: Video quality (e.g., 720p, 1080p)
- `--title TEXT`: Archive title
- `--description TEXT`: Archive description
- `--type TYPE`: Content type (channel, playlist, podcast, mixed)
- `--update-frequency FREQ`: Update frequency (e.g., 1d, 7d, 1m)

Example:
```bash
archiver-zim archive "https://www.youtube.com/watch?v=VIDEO_ID" \
  --quality 720p \
  --title "My Video Collection" \
  --description "Personal video archive" \
  --type mixed
```

## Configuration

Create a `config.yml` file with your archive configurations. Example:

```yaml
settings:
  output_base_dir: "./archives"
  quality: "best"
  retry_count: 3
  retry_delay: 5
  max_retries: 10
  max_concurrent_downloads: 3
  cleanup_after_archive: true

archives:
  - name: "youtube_channel_1"
    type: "channel"
    url: "https://www.youtube.com/c/channel1"
    update_frequency: "7d"  # 7 days
    quality: "720p"
    description: "Channel 1 Archive"
    date_limit: 30  # Only keep last 30 days

  - name: "podcast_series_1"
    type: "podcast"
    url: "https://example.com/feed.xml"
    update_frequency: "1d"  # Daily updates
    description: "Podcast Series 1 Archive"
    month_limit: 3  # Keep last 3 months
```

### Configuration Options

#### Global Settings
- `output_base_dir`: Base directory for all archives
- `quality`: Default video quality
- `retry_count`: Number of retries for failed downloads
- `retry_delay`: Base delay between retries in seconds
- `max_retries`: Maximum number of retries before giving up
- `max_concurrent_downloads`: Maximum number of concurrent downloads
- `cleanup_after_archive`: Whether to delete downloaded files after ZIM creation

#### Archive Settings
- `name`: Unique name for the archive
- `type`: Type of content ("channel", "playlist", "podcast", or "mixed")
- `url`: Source URL
- `update_frequency`: How often to update (e.g., "1d", "7d", "1m", "1y")
- `quality`: Video quality (overrides global setting)
- `description`: Archive description
- `date_limit`: Only keep content from last N days
- `month_limit`: Only keep content from last N months

## Usage

### Continuous Mode

Run the manager in continuous mode:
```bash
# Using Python
python archiver.py manage

# Using Docker
docker run -d \
  --name archiver-zim \
  -v $(pwd)/archive:/app/archive \
  -v $(pwd)/config:/app/config \
  -e TZ=UTC \
  ghcr.io/sudo-ivan/archiver-zim:latest manage

# Using Docker Compose
docker compose up -d
```

The manager will:
1. Load the configuration from `config.yml`
2. Check each archive's update frequency
3. Download and create ZIM files as needed
4. Clean up temporary files
5. Repeat the process

### Single Archive Mode

Create a single archive:
```bash
# Using Python
python archiver.py archive URL1 URL2 --output-dir ./archive --quality 720p

# Using Docker
docker run --rm \
  -v $(pwd)/archive:/app/archive \
  ghcr.io/sudo-ivan/archiver-zim:latest archive \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  --quality 720p

# Using Docker Compose
docker compose run --rm archiver archive \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  --quality 720p
```

## Logging

Logs are written to both:
- Console output
- `archive_manager.log` file

## License

MIT License