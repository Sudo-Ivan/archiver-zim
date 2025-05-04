---
layout: default
---

<div class="hero">
    <h1>Video Archiver ZIM</h1>
    <p class="lead">A powerful tool to download videos and podcasts from various platforms and create ZIM archives for offline viewing.</p>
</div>

## Features

- Download videos from multiple platforms
- Support for podcasts and RSS feeds
- Create ZIM archives for offline viewing
- Automatic updates and scheduling
- Customizable quality settings
- Concurrent downloads
- Retry mechanism for failed downloads

## Quick Start

```bash
pip install archiver-zim
```

```bash
archiver-zim archive "https://www.youtube.com/watch?v=VIDEO_ID"
```

or

```bash
archiver-zim manage
```

## Docker Installation

1. Pull the Docker image:
```bash
docker pull ghcr.io/sudo-ivan/archiver-zim:latest
```

2. Create required directories:
```bash
mkdir -p archive/media archive/metadata config
```

3. Run using Docker:
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

## Config

config.yml

```yaml
settings:
  output_base_dir: "./archives"
  quality: "best"
  retry_count: 3
  retry_delay: 5
  max_retries: 10
  max_concurrent_downloads: 3
  cleanup_after_archive: true
  cookies: null  # Path to cookies file
  cookies_from_browser: null  # Browser to extract cookies from (e.g., firefox, chrome)

archives:
  - name: "youtube_channel_1"
    type: "channel"
    url: "https://www.youtube.com/c/channel1"
    update_frequency: "7d"  # 7 days
    quality: "720p"
    description: "Channel 1 Archive"
    date_limit: 30  # Only keep last 30 days
    cookies: null  # Optional: Override global cookies
    cookies_from_browser: null  # Optional: Override global browser cookies

  - name: "podcast_series_1"
    type: "podcast"
    url: "https://example.com/feed.xml"
    update_frequency: "1d"  # Daily updates
    description: "Podcast Series 1 Archive"
    month_limit: 3  # Keep last 3 months
```

## Contributing

We welcome contributions! Please visit our [GitHub repository](https://github.com/Sudo-Ivan/archiver-zim) to get started. 