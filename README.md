# Video & Podcast Archiver ZIM

A tool to download videos from YouTube, Rumble, and Odysee, as well as podcasts from RSS feeds, and create ZIM archives for offline viewing.

## Features

- Download videos from multiple platforms (YouTube, Rumble, Odysee)
- Download podcasts from RSS feeds
- Support for channels, playlists, and individual videos
- Support for podcast episodes with date filtering
- Quality selection for videos (best, 720p, 480p, etc.)
- Date filtering for both videos and podcasts
- Create ZIM archives for offline viewing
- Rich command-line interface with progress tracking

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/video-archiver-zim.git
cd video-archiver-zim
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install yt-dlp (if not already installed):
```bash
pip install -U yt-dlp
```

## Usage

### Download Videos

Download a video or playlist:
```bash
python archiver.py archive "https://www.youtube.com/watch?v=VIDEO_ID"
```

Download with specific quality:
```bash
python archiver.py archive "https://www.youtube.com/watch?v=VIDEO_ID" --quality 720p
```

Download videos from a specific date:
```bash
python archiver.py archive "https://www.youtube.com/channel/CHANNEL_ID" --date 2024-01-01
```

### Download Podcasts

Download a podcast feed:
```bash
python archiver.py archive "https://example.com/podcast/feed.xml"
```

Download podcast episodes from the last N days:
```bash
python archiver.py archive "https://example.com/podcast/feed.xml" --date-limit 30
```

Download podcast episodes from the last N months:
```bash
python archiver.py archive "https://example.com/podcast/feed.xml" --month-limit 3
```

### Create ZIM Archive

Create a ZIM archive from downloaded media:
```bash
python archiver.py archive "My Media Archive" --description "Collection of videos and podcasts"
```

Additional options:
```bash
python archiver.py archive [URLS] [OPTIONS]

Options:
  --output-dir, -o TEXT    Output directory [default: ./archive]
  --quality, -q TEXT       Video quality (e.g., 720p, 480p) [default: best]
  --date, -d TEXT         Filter by specific date (YYYY-MM-DD)
  --date-limit, -dl INTEGER  Download only episodes from the last N days
  --month-limit, -ml INTEGER  Download only episodes from the last N months
  --title, -t TEXT        Title for the ZIM archive
  --description, --desc TEXT  ZIM archive description [default: Media archive]
  --retry-count INTEGER   Number of retries for failed downloads [default: 3]
  --retry-delay INTEGER   Base delay between retries in seconds [default: 5]
  --max-retries INTEGER   Maximum number of retries before giving up [default: 10]
  --skip-download         Skip download phase and create ZIM from existing media
  --cleanup              Delete downloaded files after ZIM creation
  --dry-run              Simulate operations without downloading
```

## Supported Platforms

### Video Platforms
- YouTube
- Rumble
- Odysee

### Podcast Formats
- RSS feeds
- Atom feeds
- JSON feeds

## Features

### Video Features
- YouTube-style interface
- Playlist organization
- Quality selection
- Date filtering
- Subtitle support
- Chapter navigation

### Podcast Features
- RSS feed support
- Date-based filtering
- Episode organization
- Metadata preservation
- Audio format support

## License

MIT License 