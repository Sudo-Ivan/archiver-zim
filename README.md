# Archiver ZIM

A tool for continuously downloading and archiving videos and podcasts into ZIM files.

## Features

- Continuous running mode for automatic updates
- Support for YouTube channels, playlists, and podcast feeds
- Configurable update frequencies
- Mixed content archives
- Automatic cleanup after archiving
- Rich progress tracking and logging

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Install yt-dlp (required for video downloads):
```bash
pip install yt-dlp
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
python archiver.py manage
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
python archiver.py archive URL1 URL2 --output-dir ./archive --quality 720p
```

## Logging

Logs are written to both:
- Console output
- `archive_manager.log` file

## License

MIT License 