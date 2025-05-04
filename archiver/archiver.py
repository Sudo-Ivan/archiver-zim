#!/usr/bin/env python3

"""Archiver ZIM - A tool to download videos and podcasts from various platforms and create ZIM archives."""

# Copyright (c) 2025 Sudo-Ivan
# Licensed under the MIT License (see LICENSE file for details)

import sys
import json
import logging
import subprocess
import threading
import random
import time
import feedparser
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from libzim.writer import Creator, Item, StringProvider, FileProvider, Hint
import asyncio
import shutil

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True, show_time=False)]
)
log = logging.getLogger("archiver")
console = Console()

class OutputFilter(logging.Filter):
    """Add a custom filter to separate debug messages and command line config."""
    def filter(self, record):
        msg = record.getMessage()
        return not any([
            msg.startswith('[debug]'),
            msg.startswith('Command-line config:'),
            msg.startswith('Encodings:'),
            'Downloading webpage' in msg,
            'Redownloading playlist API JSON' in msg,
            'page 1: Downloading API JSON' in msg,
            'Downloading tv client config' in msg,
            'ios client https formats require a GVS PO Token' in msg
        ])

logging.getLogger().addFilter(OutputFilter())

class MediaItem(Item):
    """Custom Item class for media content."""

    def __init__(self, title: str, path: str, content: str = "", fpath: Optional[str] = None):
        """
        Initialize a MediaItem.

        Args:
            title: The title of the media item.
            path: The path for the media item in the ZIM archive.
            content: The HTML content of the media item.
            fpath: The file path to the media item, if it exists.
        """
        super().__init__()
        self.path = path
        self.title = title
        self.content = content
        self.fpath = fpath

    def get_path(self):
        """Return the path of the media item."""
        return self.path

    def get_title(self):
        """Return the title of the media item."""
        return self.title

    def get_mimetype(self):
        """Return the MIME type of the media item."""
        return "text/html"

    def get_contentprovider(self):
        """Return the content provider for the media item."""
        if self.fpath is not None:
            return FileProvider(self.fpath)
        return StringProvider(self.content)

    def get_hints(self):
        """Return hints for the media item."""
        return {Hint.FRONT_ARTICLE: True}

class Archiver:
    """Main class for media archiving functionality."""

    def __init__(self, output_dir: str, quality: str = "best", retry_count: int = 3,
                 retry_delay: int = 5, max_retries: int = 10, max_concurrent_downloads: int = 3,
                 dry_run: bool = False):
        """
        Initialize the Archiver.

        Args:
            output_dir: Directory to store downloaded media and ZIM files.
            quality: Video quality setting (e.g., "best", "720p", "480p").
            retry_count: Number of retries for failed downloads.
            retry_delay: Base delay between retries in seconds.
            max_retries: Maximum number of retries before giving up.
            max_concurrent_downloads: Maximum number of concurrent downloads.
            dry_run: If True, only simulate operations without downloading.
        """
        self.output_dir = Path(output_dir)
        self.quality = quality
        self.media_dir = self.output_dir / "media"
        self.metadata_dir = self.output_dir / "metadata"
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.max_concurrent_downloads = max_concurrent_downloads
        self.download_semaphore = asyncio.Semaphore(max_concurrent_downloads)
        self.download_progress: Dict[str, float] = {}
        self.dry_run = dry_run
        self.logger = logging.getLogger("archiver")

        try:
            yt_dlp_path = shutil.which("yt-dlp")
            if not yt_dlp_path:
                raise RuntimeError("yt-dlp is not installed or not in PATH")

            result = subprocess.run([yt_dlp_path, "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("yt-dlp is not properly installed")
            self.logger.info(f"Using yt-dlp version: {result.stdout.strip()}")
        except Exception as e:
            raise RuntimeError(f"Failed to check yt-dlp installation: {e}")

        if not dry_run:
            self.media_dir.mkdir(parents=True, exist_ok=True)
            self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def get_archive_info(self) -> Dict[str, Any]:
        """
        Get information about the current archive state.

        Returns:
            Dict containing archive information.
        """
        return {
            "output_dir": str(self.output_dir),
            "media_count": len(list(self.media_dir.glob("*"))) if self.media_dir.exists() else 0,
            "metadata_count": len(list(self.metadata_dir.glob("*"))) if self.metadata_dir.exists() else 0,
            "last_update": datetime.now().isoformat() if self.media_dir.exists() else None
        }

    @staticmethod
    def _get_random_user_agent() -> str:
        """Get a random user agent to avoid detection."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        ]
        return random.choice(user_agents)

    @staticmethod
    def _add_random_delay():
        """Add a random delay to avoid rate limiting."""
        delay = random.uniform(1, 3)
        time.sleep(delay)

    async def _download_video_async(self, url: str, date: Optional[str] = None) -> bool:
        """
        Asynchronously download a video with retry logic.

        Args:
            url: The URL of the video to download.
            date: An optional date to filter the video by.

        Returns:
            True if the download was successful, False otherwise.
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would download video from {url}")
            return True

        async with self.download_semaphore:
            retries = 0
            while retries < self.max_retries:
                try:
                    cmd = [
                        "yt-dlp",
                        "--write-description",
                        "--write-info-json",
                        "--write-thumbnail",
                        "--no-playlist-reverse",
                        "--user-agent", self._get_random_user_agent(),
                        "--socket-timeout", "60",
                        "--retries", str(self.retry_count),
                        "--fragment-retries", str(self.retry_count),
                        "--file-access-retries", str(self.retry_count),
                        "--extractor-retries", str(self.retry_count),
                        "--ignore-errors",
                        "--no-warnings",
                        "--progress",
                        "--newline",
                        "--write-sub",
                        "--write-auto-sub",
                        "--embed-chapters",
                        "--max-filesize", "2G",
                        "--throttled-rate", "100K",
                        "--retry-sleep", "5",
                        "-o", str(self.media_dir / "%(id)s.%(ext)s"),
                        "--merge-output-format", "mp4",
                        "--verbose",
                        "--extractor-args", "youtube:formats=missing_pot"
                    ]

                    if self.quality != "best":
                        cmd.extend(["-f", f"bestvideo[height<={self.quality[:-1]}]+bestaudio/best[height<={self.quality[:-1]}]"])

                    if date:
                        cmd.extend(["--date", date])

                    if "playlist" in url.lower():
                        cmd.extend([
                            "--yes-playlist",
                            "--playlist-reverse",
                            "--max-downloads", "50",
                            "--break-on-existing",
                            "--break-on-reject",
                            "--concurrent-fragments", "1",
                        ])

                    cmd.append(url)

                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )

                    output_lines = []
                    error_lines = []
                    current_progress = 0
                    current_file = ""

                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TaskProgressColumn(),
                        TimeRemainingColumn(),
                        console=console,
                        transient=True,
                        refresh_per_second=10,
                        expand=True
                    ) as progress:
                        task = progress.add_task("Downloading...", total=100)

                        while True:
                            try:
                                stdout_line = await asyncio.wait_for(process.stdout.readline(), timeout=300)
                                stderr_line = await asyncio.wait_for(process.stderr.readline(), timeout=300)

                                if not stdout_line and not stderr_line:
                                    break

                                if stdout_line:
                                    line_str = stdout_line.decode().strip()
                                    output_lines.append(line_str)

                                    if "[download]" in line_str:
                                        if "Destination:" in line_str:
                                            current_file = line_str.split("Destination:")[1].strip()
                                            progress.update(task, description=f"Downloading {current_file}")
                                        elif "%" in line_str:
                                            try:
                                                if "of" in line_str:
                                                    parts = line_str.split()
                                                    percent = float(parts[1].replace('%', ''))
                                                    current_progress = percent
                                                else:
                                                    percent = float(line_str.split('%')[0].split()[-1])
                                                    current_progress = percent

                                                progress.update(task, completed=current_progress)
                                            except (ValueError, IndexError):
                                                pass
                                        elif "has already been downloaded" in line_str:
                                            progress.update(task, completed=100, description=f"Already downloaded {current_file}")
                                    elif "[info]" in line_str:
                                        if "Downloading playlist:" in line_str:
                                            self.logger.info(f"[yellow]📋 {line_str}[/yellow]")
                                        elif "Writing playlist" in line_str:
                                            self.logger.info(f"[green]✓ {line_str}[/green]")
                                        elif "Downloading" in line_str and "thumbnail" in line_str:
                                            self.logger.info(f"[blue]🖼️ {line_str}[/blue]")
                                        elif "Downloading" in line_str and "items of" in line_str:
                                            self.logger.info(f"[cyan]📥 {line_str}[/cyan]")
                                    elif not line_str.startswith('[debug]'):
                                        self.logger.info(f"[cyan]ℹ️ {line_str}[/cyan]")

                                if stderr_line:
                                    line_str = stderr_line.decode().strip()
                                    error_lines.append(line_str)
                                    if "error" in line_str.lower():
                                        self.logger.error(f"[red]❌ {line_str}[/red]")
                                    elif not line_str.startswith('[debug]'):
                                        self.logger.warning(f"[yellow]⚠️ {line_str}[/yellow]")

                            except asyncio.TimeoutError:
                                self.logger.warning("[yellow]⚠️ Download timeout, retrying...[/yellow]")
                                process.terminate()
                                raise TimeoutError("Download operation timed out")

                    await process.wait()

                    if process.returncode != 0:
                        error_msg = "\n".join(error_lines) if error_lines else "\n".join(output_lines[-10:])
                        raise subprocess.CalledProcessError(process.returncode, cmd, error_msg)

                    for file in self.media_dir.glob("*"):
                        if file.suffix in ['.description', '.info.json', '.jpg', '.webp', '.vtt', '.srt']:
                            new_path = self.metadata_dir / file.name
                            file.rename(new_path)

                    return True

                except (TimeoutError, subprocess.CalledProcessError, Exception) as e:
                    retries += 1
                    if retries >= self.max_retries:
                        error_msg = str(e)
                        if isinstance(e, subprocess.CalledProcessError) and e.output:
                            error_msg = e.output
                        if "playlist" in url.lower():
                            error_msg += "\nPlaylist download failed. Please check if the playlist is public and accessible."
                            error_msg += "\nTry downloading with a lower concurrent download limit or in smaller batches."
                        self.logger.error(f"[red]❌ Failed to download video after {self.max_retries} attempts: {error_msg}[/red]")
                        return False

                    delay = self.retry_delay * (2 ** retries)
                    self.logger.warning(f"[yellow]⚠️ Download failed, retrying in {delay} seconds... (Attempt {retries}/{self.max_retries})[/yellow]")
                    await asyncio.sleep(delay)
                    self._add_random_delay()

    async def _download_podcast_async(self, url: str, date_limit: Optional[int] = None, month_limit: Optional[int] = None) -> bool:
        """
        Asynchronously download a podcast feed with retry logic.

        Args:
            url: The URL of the podcast feed to download.
            date_limit: Download only episodes from the last N days.
            month_limit: Download only episodes from the last N months.

        Returns:
            True if the download was successful, False otherwise.
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would download podcast from {url}")
            return True

        async with self.download_semaphore:
            retries = 0
            while retries < self.max_retries:
                try:
                    headers = {'User-Agent': self._get_random_user_agent()}
                    response = requests.get(url, headers=headers, timeout=30)
                    response.raise_for_status()

                    feed = feedparser.parse(response.content)
                    if not feed.entries:
                        raise ValueError("No entries found in feed")

                    now = datetime.now()
                    if date_limit:
                        date_cutoff = now - timedelta(days=date_limit)
                    elif month_limit:
                        date_cutoff = now - timedelta(days=30 * month_limit)
                    else:
                        date_cutoff = None

                    feed_metadata = {
                        'title': feed.feed.title,
                        'description': feed.feed.description if hasattr(feed.feed, 'description') else '',
                        'entries': []
                    }

                    filtered_entries = []
                    for entry in feed.entries:
                        published_date = None
                        if hasattr(entry, 'published_parsed'):
                            published_date = datetime(*entry.published_parsed[:6])
                        elif hasattr(entry, 'updated_parsed'):
                            published_date = datetime(*entry.updated_parsed[:6])

                        if date_cutoff and published_date and published_date < date_cutoff:
                            continue

                        entry_data = {
                            'title': entry.title,
                            'description': entry.description if hasattr(entry, 'description') else '',
                            'published': entry.published if hasattr(entry, 'published') else '',
                            'published_date': published_date.isoformat() if published_date else None,
                            'enclosures': []
                        }

                        for enclosure in entry.get('enclosures', []):
                            if 'url' in enclosure and 'type' in enclosure:
                                entry_data['enclosures'].append({
                                    'url': enclosure['url'],
                                    'type': enclosure['type'],
                                    'length': enclosure.get('length', '')
                                })

                        feed_metadata['entries'].append(entry_data)
                        filtered_entries.append(entry)

                    if not filtered_entries:
                        self.logger.warning(f"No entries found within the specified date range for {url}")
                        return True

                    feed_id = url.split('/')[-1].split('.')[0]
                    metadata_file = self.metadata_dir / f"{feed_id}.json"
                    with open(metadata_file, 'w') as f:
                        json.dump(feed_metadata, f, indent=2)

                    total_enclosures = sum(len(entry['enclosures']) for entry in feed_metadata['entries'])
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TaskProgressColumn(),
                        TimeRemainingColumn(),
                        console=console
                    ) as progress:
                        task = progress.add_task("Downloading podcast episodes...", total=total_enclosures)

                        for entry in feed_metadata['entries']:
                            for enclosure in entry['enclosures']:
                                if enclosure['type'].startswith(('audio/', 'video/')):
                                    enclosure_url = enclosure['url']
                                    enclosure_filename = enclosure_url.split('/')[-1]
                                    enclosure_path = self.media_dir / enclosure_filename

                                    if not enclosure_path.exists():
                                        response = requests.get(enclosure_url, headers=headers, stream=True, timeout=30)
                                        response.raise_for_status()

                                        total_size = int(response.headers.get('content-length', 0))
                                        block_size = 8192
                                        downloaded = 0

                                        with open(enclosure_path, 'wb') as f:
                                            for chunk in response.iter_content(chunk_size=block_size):
                                                if chunk:
                                                    f.write(chunk)
                                                    downloaded += len(chunk)
                                                    if total_size > 0:
                                                        progress.update(task, completed=downloaded, total=total_size)

                                        progress.update(task, advance=1)
                                        self.logger.info(f"Downloaded: {enclosure_filename}")

                    return True

                except Exception as e:
                    retries += 1
                    if retries >= self.max_retries:
                        self.logger.error(f"Failed to download podcast after {self.max_retries} attempts: {e}")
                        return False

                    delay = self.retry_delay * (2 ** retries)
                    self.logger.warning(f"Download failed, retrying in {delay} seconds... (Attempt {retries}/{self.max_retries})")
                    await asyncio.sleep(delay)
                    self._add_random_delay()

    async def download_media_async(self, urls: List[str], date: Optional[str] = None,
                                 date_limit: Optional[int] = None, month_limit: Optional[int] = None) -> Dict[str, bool]:
        """
        Download multiple media items concurrently.

        Args:
            urls: A list of media URLs to download.
            date: An optional date to filter videos by.
            date_limit: Download only podcast episodes from the last N days.
            month_limit: Download only podcast episodes from the last N months.

        Returns:
            A dictionary mapping each URL to a boolean indicating whether the download was successful.
        """
        tasks = []
        for url in urls:
            if any(url.endswith(ext) for ext in ['.xml', '.atom', '.json', '.rss']):
                tasks.append(self._download_podcast_async(url, date_limit, month_limit))
            else:
                tasks.append(self._download_video_async(url, date))
        results = await asyncio.gather(*tasks)
        return dict(zip(urls, results))

    def download_media(self, urls: List[str], date: Optional[str] = None,
                      date_limit: Optional[int] = None, month_limit: Optional[int] = None) -> Dict[str, bool]:
        """
        Download multiple media items with progress tracking.

        Args:
            urls: A list of media URLs to download.
            date: An optional date to filter videos by.
            date_limit: Download only podcast episodes from the last N days.
            month_limit: Download only podcast episodes from the last N months.

        Returns:
            A dictionary mapping each URL to a boolean indicating whether the download was successful.
        """
        return asyncio.run(self.download_media_async(urls, date, date_limit, month_limit))

    @staticmethod
    def verify_download(file_path: Path) -> bool:
        """
        Verify the download of a media file.

        Args:
            file_path: The path to the downloaded file.

        Returns:
            True if the file exists and is a file, False otherwise.
        """
        return file_path.exists() and file_path.is_file()

    def _get_media_metadata(self, media_file: Path) -> Dict[str, Any]:
        """
        Extract media metadata including chapters and subtitles.

        Args:
            media_file: The path to the media file.

        Returns:
            A dictionary containing the media metadata.
        """
        metadata = {}
        json_file = media_file.with_suffix(".info.json")

        if json_file.exists():
            try:
                with open(json_file) as f:
                    metadata = json.load(f)
                    if 'title' in metadata:
                        metadata['title'] = metadata['title'].strip()
                    if 'description' in metadata:
                        metadata['description'] = metadata['description'].strip()
                    if 'upload_date' in metadata:
                        try:
                            date = datetime.strptime(metadata['upload_date'], '%Y%m%d')
                            metadata['upload_date'] = date.strftime('%B %d, %Y')
                        except ValueError:
                            pass
                    if 'playlist' in metadata:
                        metadata['playlist_title'] = metadata['playlist'].get('title', '')
                        metadata['playlist_index'] = metadata['playlist'].get('index', 0)
                        metadata['playlist_id'] = metadata['playlist'].get('id', '')
            except Exception as e:
                self.logger.error(f"Error reading metadata for {media_file.name}: {e}")
                return metadata

        subtitle_files = list(self.metadata_dir.glob(f"{media_file.stem}*.vtt")) + \
                        list(self.metadata_dir.glob(f"{media_file.stem}*.srt"))
        if subtitle_files:
            metadata['subtitles'] = [str(f.name) for f in subtitle_files]
        else:
            self.logger.info(f"No subtitles found for {media_file.name}")

        if 'chapters' not in metadata:
            self.logger.info(f"No chapters found for {media_file.name}")

        return metadata

    def create_zim(self, title: str, description: str) -> bool:
        """
        Create a ZIM file from downloaded media.

        Args:
            title: The title of the ZIM archive.
            description: A description of the ZIM archive.

        Returns:
            True if the ZIM archive was created successfully, False otherwise.
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would create ZIM archive with title: {title}")
            return True

        try:
            zim_path = self.output_dir / f"{title.lower().replace(' ', '_')}.zim"
            lock = threading.Lock()

            with Creator(str(zim_path)).config_indexing(True, "eng") as creator:
                metadata = {
                    "creator": "Archiver ZIM",
                    "description": description,
                    "name": title.lower().replace(' ', '_'),
                    "publisher": "Archiver",
                    "title": title,
                    "language": "eng",
                    "date": datetime.now().strftime("%Y-%m-%d")
                }

                for name, value in metadata.items():
                    creator.add_metadata(name.title(), value)

                creator.set_mainpath("index")

                media_files = list(self.media_dir.glob("*.*"))
                playlist_groups = {}
                standalone_videos = []

                for media_file in media_files:
                    if media_file.suffix not in ['.info.json', '.description', '.jpg', '.webp', '.vtt', '.srt']:
                        media_metadata = self._get_media_metadata(media_file)
                        if 'playlist_id' in media_metadata and media_metadata['playlist_id']:
                            playlist_id = media_metadata['playlist_id']
                            if playlist_id not in playlist_groups:
                                playlist_groups[playlist_id] = {
                                    'title': media_metadata.get('playlist_title', ''),
                                    'videos': []
                                }
                            playlist_groups[playlist_id]['videos'].append((media_file, media_metadata))
                        else:
                            standalone_videos.append((media_file, media_metadata))

                for playlist in playlist_groups.values():
                    playlist['videos'].sort(key=lambda x: x[1].get('playlist_index', 0))

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeRemainingColumn(),
                    console=console,
                    transient=True,
                    refresh_per_second=10,
                    expand=True
                ) as progress:
                    task = progress.add_task("Creating ZIM archive...", total=len(media_files))

                    for media_file, media_metadata in standalone_videos + [v for p in playlist_groups.values() for v in p['videos']]:
                        with lock:
                            try:
                                mime_type = "video/mp4" if media_file.suffix == ".mp4" else "audio/mpeg"

                                html_content = f"""
                                <!DOCTYPE html>
                                <html>
                                <head>
                                    <title>{media_metadata.get('title', media_file.stem)}</title>
                                    <meta charset="utf-8">
                                    <style>
                                        body {{
                                            font-family: Arial, sans-serif;
                                            line-height: 1.6;
                                            max-width: 1200px;
                                            margin: 0 auto;
                                            padding: 20px;
                                            background-color: #f9f9f9;
                                        }}
                                        .media-container {{
                                            width: 100%;
                                            margin: 20px 0;
                                            background-color: #000;
                                            position: relative;
                                            padding-top: 56.25%; /* 16:9 Aspect Ratio */
                                        }}
                                        video, audio {{
                                            position: absolute;
                                            top: 0;
                                            left: 0;
                                            width: 100%;
                                            height: 100%;
                                        }}
                                        .video-info {{
                                            margin: 20px 0;
                                            padding: 20px;
                                            background: #fff;
                                            border-radius: 8px;
                                            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                                        }}
                                        .video-title {{
                                            font-size: 24px;
                                            font-weight: bold;
                                            margin-bottom: 10px;
                                            color: #030303;
                                        }}
                                        .video-meta {{
                                            color: #606060;
                                            font-size: 14px;
                                            margin-bottom: 20px;
                                        }}
                                        .playlist-info {{
                                            margin-bottom: 20px;
                                            padding: 10px;
                                            background: #f8f8f8;
                                            border-radius: 4px;
                                        }}
                                        .playlist-info a {{
                                            color: #065fd4;
                                            text-decoration: none;
                                        }}
                                        .playlist-info a:hover {{
                                            text-decoration: underline;
                                        }}
                                        .video-description {{
                                            white-space: pre-wrap;
                                            word-wrap: break-word;
                                            color: #030303;
                                            font-size: 14px;
                                            line-height: 1.5;
                                            border-top: 1px solid #e5e5e5;
                                            padding-top: 20px;
                                        }}
                                        .chapters {{
                                            margin: 20px 0;
                                            padding: 20px;
                                            background: #fff;
                                            border-radius: 8px;
                                            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                                        }}
                                        .chapters h3 {{
                                            margin: 0 0 15px 0;
                                            color: #030303;
                                        }}
                                        .chapters ul {{
                                            list-style-type: none;
                                            padding: 0;
                                            margin: 0;
                                        }}
                                        .chapters li {{
                                            margin: 8px 0;
                                            padding: 8px 12px;
                                            cursor: pointer;
                                            border-radius: 4px;
                                            transition: background-color 0.2s;
                                        }}
                                        .chapters li:hover {{
                                            background-color: #f2f2f2;
                                        }}
                                    </style>
                                </head>
                                <body>
                                    <div class="video-info">
                                        <h1 class="video-title">{media_metadata.get('title', media_file.stem)}</h1>
                                        <div class="video-meta">
                                            {media_metadata.get('upload_date', '')}
                                        </div>
                                """

                                if 'playlist_id' in media_metadata and media_metadata['playlist_id']:
                                    playlist = playlist_groups[media_metadata['playlist_id']]
                                    html_content += f"""
                                        <div class="playlist-info">
                                            Part of playlist: <a href="playlist_{media_metadata['playlist_id']}">{playlist['title']}</a>
                                            (Video {media_metadata.get('playlist_index', 0)} of {len(playlist['videos'])})
                                        </div>
                                    """

                                html_content += """
                                    </div>
                                    <div class="media-container">
                                """

                                if mime_type.startswith('video/'):
                                    html_content += f"""
                                        <video controls>
                                            <source src="{media_file.name}" type="{mime_type}">
                                            Your browser does not support the video tag.
                                        </video>
                                    """
                                else:
                                    html_content += f"""
                                        <audio controls>
                                            <source src="{media_file.name}" type="{mime_type}">
                                            Your browser does not support the audio tag.
                                        </audio>
                                    """

                                html_content += "</div>"

                                if 'subtitles' in media_metadata:
                                    for subtitle in media_metadata['subtitles']:
                                        html_content += f'<track src="{subtitle}" kind="subtitles" label="{subtitle.split(".")[-1].upper()}">\n'

                                if 'chapters' in media_metadata:
                                    html_content += '<div class="chapters"><h3>Chapters</h3><ul>\n'
                                    for chapter in media_metadata['chapters']:
                                        start_time = chapter.get('start_time', 0)
                                        title = chapter.get('title', 'Untitled')
                                        html_content += f'<li onclick="document.querySelector(\'video,audio\').currentTime = {start_time}">{title}</li>\n'
                                    html_content += '</ul></div>\n'

                                if 'description' in media_metadata:
                                    html_content += f"""
                                        <div class="video-info">
                                            <div class="video-description">{media_metadata['description']}</div>
                                        </div>
                                    """

                                html_content += """
                                </body>
                                </html>
                                """

                                media_item = MediaItem(
                                    title=media_metadata.get('title', media_file.stem),
                                    path=f"media/{media_file.stem}",
                                    content=html_content
                                )
                                creator.add_item(media_item)

                                media_file_item = MediaItem(
                                    title=media_file.name,
                                    path=f"media/{media_file.name}",
                                    fpath=str(media_file)
                                )
                                media_file_item.get_mimetype = lambda: mime_type
                                creator.add_item(media_file_item)

                                if 'subtitles' in media_metadata:
                                    for subtitle in media_metadata['subtitles']:
                                        subtitle_path = self.metadata_dir / subtitle
                                        if subtitle_path.exists():
                                            subtitle_item = MediaItem(
                                                title=subtitle,
                                                path=f"media/{subtitle}",
                                                fpath=str(subtitle_path)
                                            )
                                            subtitle_item.get_mimetype = lambda: "text/vtt" if subtitle.endswith('.vtt') else "text/srt"
                                            creator.add_item(subtitle_item)

                            except Exception as e:
                                self.logger.error(f"Error processing media {media_file.name}: {e}")
                                continue

                            progress.update(task, advance=1)

                for playlist_id, playlist in playlist_groups.items():
                    playlist_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>{playlist['title']}</title>
                        <meta charset="utf-8">
                        <style>
                            body {{
                                font-family: Arial, sans-serif;
                                line-height: 1.6;
                                max-width: 1200px;
                                margin: 0 auto;
                                padding: 20px;
                                background-color: #f9f9f9;
                            }}
                            h1 {{
                                color: #030303;
                                margin-bottom: 20px;
                            }}
                            .playlist-info {{
                                color: #606060;
                                margin-bottom: 30px;
                            }}
                            .video-grid {{
                                display: grid;
                                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                                gap: 20px;
                                padding: 0;
                            }}
                            .video-item {{
                                background: #fff;
                                border-radius: 8px;
                                overflow: hidden;
                                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                                transition: transform 0.2s;
                            }}
                            .video-item:hover {{
                                transform: translateY(-2px);
                            }}
                            .video-item a {{
                                text-decoration: none;
                                color: inherit;
                            }}
                            .video-thumbnail {{
                                width: 100%;
                                padding-top: 56.25%;
                                background-color: #000;
                                position: relative;
                            }}
                            .video-thumbnail img {{
                                position: absolute;
                                top: 0;
                                left: 0;
                                width: 100%;
                                height: 100%;
                                object-fit: cover;
                            }}
                            .video-info {{
                                padding: 12px;
                            }}
                            .video-title {{
                                font-weight: bold;
                                color: #030303;
                                margin-bottom: 4px;
                                display: -webkit-box;
                                -webkit-line-clamp: 2;
                                -webkit-box-orient: vertical;
                                overflow: hidden;
                            }}
                            .video-date {{
                                color: #606060;
                                font-size: 12px;
                            }}
                            .video-index {{
                                color: #606060;
                                font-size: 12px;
                                margin-top: 4px;
                            }}
                        </style>
                    </head>
                    <body>
                        <h1>{playlist['title']}</h1>
                        <div class="playlist-info">
                            {len(playlist['videos'])} videos in this playlist
                        </div>
                        <div class="video-grid">
                    """

                    for media_file, media_metadata in playlist['videos']:
                        title = media_metadata.get('title', media_file.stem)
                        date = media_metadata.get('upload_date', '')
                        thumbnail = media_metadata.get('thumbnail', '')
                        index = media_metadata.get('playlist_index', 0)

                        playlist_content += f"""
                        <div class="video-item">
                            <a href="media/{media_file.stem}">
                                <div class="video-thumbnail">
                                    <img src="{thumbnail}" alt="{title}">
                                </div>
                                <div class="video-info">
                                    <div class="video-title">{title}</div>
                                    <div class="video-date">{date}</div>
                                    <div class="video-index">Video {index}</div>
                                </div>
                            </a>
                        </div>
                        """

                    playlist_content += """
                        </div>
                    </body>
                    </html>
                    """

                    playlist_item = MediaItem(
                        title=playlist['title'],
                        path=f"playlist_{playlist_id}",
                        content=playlist_content
                    )
                    creator.add_item(playlist_item)

                index_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{title}</title>
                    <meta charset="utf-8">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            line-height: 1.6;
                            max-width: 1200px;
                            margin: 0 auto;
                            padding: 20px;
                            background-color: #f9f9f9;
                        }}
                        h1 {{
                            color: #030303;
                            margin-bottom: 20px;
                        }}
                        .description {{
                            color: #606060;
                            margin-bottom: 30px;
                        }}
                        .section {{
                            margin-bottom: 40px;
                        }}
                        .section-title {{
                            font-size: 24px;
                            font-weight: bold;
                            color: #030303;
                            margin-bottom: 20px;
                            padding-bottom: 10px;
                            border-bottom: 1px solid #e5e5e5;
                        }}
                        .video-grid {{
                            display: grid;
                            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                            gap: 20px;
                            padding: 0;
                        }}
                        .video-item {{
                            background: #fff;
                            border-radius: 8px;
                            overflow: hidden;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                            transition: transform 0.2s;
                        }}
                        .video-item:hover {{
                            transform: translateY(-2px);
                        }}
                        .video-item a {{
                            text-decoration: none;
                            color: inherit;
                        }}
                        .video-thumbnail {{
                            width: 100%;
                            padding-top: 56.25%;
                            background-color: #000;
                            position: relative;
                        }}
                        .video-thumbnail img {{
                            position: absolute;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            object-fit: cover;
                        }}
                        .video-info {{
                            padding: 12px;
                        }}
                        .video-title {{
                            font-weight: bold;
                            color: #030303;
                            margin-bottom: 4px;
                            display: -webkit-box;
                            -webkit-line-clamp: 2;
                            -webkit-box-orient: vertical;
                            overflow: hidden;
                        }}
                        .video-date {{
                            color: #606060;
                            font-size: 12px;
                        }}
                        .playlist-card {{
                            background: #fff;
                            border-radius: 8px;
                            overflow: hidden;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                            transition: transform 0.2s;
                        }}
                        .playlist-card:hover {{
                            transform: translateY(-2px);
                        }}
                        .playlist-card a {{
                            text-decoration: none;
                            color: inherit;
                        }}
                        .playlist-thumbnail {{
                            width: 100%;
                            padding-top: 56.25%;
                            background-color: #000;
                            position: relative;
                        }}
                        .playlist-thumbnail img {{
                            position: absolute;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            object-fit: cover;
                        }}
                        .playlist-info {{
                            padding: 12px;
                        }}
                        .playlist-title {{
                            font-weight: bold;
                            color: #030303;
                            margin-bottom: 4px;
                        }}
                        .playlist-count {{
                            color: #606060;
                            font-size: 12px;
                        }}
                    </style>
                </head>
                <body>
                    <h1>{title}</h1>
                    <div class="description">{description}</div>
                """

                if playlist_groups:
                    index_content += """
                        <div class="section">
                            <h2 class="section-title">Playlists</h2>
                            <div class="video-grid">
                    """
                    for playlist_id, playlist in playlist_groups.items():
                        # Use the first video's thumbnail as playlist thumbnail
                        first_video = playlist['videos'][0]
                        thumbnail = first_video[1].get('thumbnail', '')

                        index_content += f"""
                            <div class="playlist-card">
                                <a href="playlist_{playlist_id}">
                                    <div class="playlist-thumbnail">
                                        <img src="{thumbnail}" alt="{playlist['title']}">
                                    </div>
                                    <div class="playlist-info">
                                        <div class="playlist-title">{playlist['title']}</div>
                                        <div class="playlist-count">{len(playlist['videos'])} videos</div>
                                    </div>
                                </a>
                            </div>
                        """
                    index_content += """
                            </div>
                        </div>
                    """

                if standalone_videos:
                    index_content += """
                        <div class="section">
                            <h2 class="section-title">Videos</h2>
                            <div class="video-grid">
                    """
                    for media_file, media_metadata in standalone_videos:
                        title = media_metadata.get('title', media_file.stem)
                        date = media_metadata.get('upload_date', '')
                        thumbnail = media_metadata.get('thumbnail', '')

                        index_content += f"""
                            <div class="video-item">
                                <a href="media/{media_file.stem}">
                                    <div class="video-thumbnail">
                                        <img src="{thumbnail}" alt="{title}">
                                    </div>
                                    <div class="video-info">
                                        <div class="video-title">{title}</div>
                                        <div class="video-date">{date}</div>
                                    </div>
                                </a>
                            </div>
                        """
                    index_content += """
                            </div>
                        </div>
                    """

                index_content += """
                </body>
                </html>
                """

                index_item = MediaItem(
                    title=title,
                    path="index",
                    content=index_content
                )
                creator.add_item(index_item)

            log.info(f"Created ZIM archive at {zim_path}")
            return True

        except Exception as e:
            log.error(f"Failed to create ZIM archive: {e}")
            return False

    def cleanup(self) -> None:
        """
        Delete all downloaded files and directories after ZIM creation.

        This method attempts to remove all files within the media and metadata directories,
        and then removes the directories themselves. It logs each deletion attempt and
        any errors encountered. If directory removal fails, it lists any remaining files
        in those directories.
        """
        try:
            if self.media_dir.exists():
                for file in self.media_dir.glob("*"):
                    try:
                        file.unlink()
                        log.info(f"Deleted media file: {file.name}")
                    except Exception as e:
                        log.warning(f"Could not delete file {file.name}: {e}")

            if self.metadata_dir.exists():
                for file in self.metadata_dir.glob("*"):
                    try:
                        file.unlink()
                        log.info(f"Deleted metadata file: {file.name}")
                    except Exception as e:
                        log.warning(f"Could not delete file {file.name}: {e}")

            try:
                if self.media_dir.exists():
                    self.media_dir.rmdir()
                if self.metadata_dir.exists():
                    self.metadata_dir.rmdir()
                log.info("Cleanup completed successfully")
            except Exception as e:
                log.warning(f"Could not remove directories: {e}")
                if self.media_dir.exists():
                    remaining = list(self.media_dir.glob("*"))
                    if remaining:
                        log.warning(f"Remaining files in media directory: {[f.name for f in remaining]}")
                if self.metadata_dir.exists():
                    remaining = list(self.metadata_dir.glob("*"))
                    if remaining:
                        log.warning(f"Remaining files in metadata directory: {[f.name for f in remaining]}")

        except Exception as e:
            log.error(f"Error during cleanup: {e}")
            try:
                if self.media_dir.exists():
                    log.error(f"Files still in media directory: {[f.name for f in self.media_dir.glob('*')]}")
                if self.metadata_dir.exists():
                    log.error(f"Files still in metadata directory: {[f.name for f in self.metadata_dir.glob('*')]}")
            except Exception as e:
                log.error(f"Failed to list remaining files: {e}")

@click.group()
def cli():
    """Archiver ZIM - Download videos and podcasts and create ZIM archives."""
    pass

@cli.command()
@click.argument('urls', nargs=-1, required=True)
@click.option('--output-dir', '-o', default='./archive', help='Output directory')
@click.option('--quality', '-q', default='best', help='Video quality (e.g., 720p, 480p)')
@click.option('--date', '-d', help='Filter by specific date (YYYY-MM-DD)')
@click.option('--date-limit', '-dl', type=int, help='Download only episodes from the last N days')
@click.option('--month-limit', '-ml', type=int, help='Download only episodes from the last N months')
@click.option('--title', '-t', help='Title for the ZIM archive')
@click.option('--description', '--desc', default='Media archive', help='ZIM archive description')
@click.option('--retry-count', default=3, help='Number of retries for failed downloads')
@click.option('--retry-delay', default=5, help='Base delay between retries in seconds')
@click.option('--max-retries', default=10, help='Maximum number of retries before giving up')
@click.option('--skip-download', is_flag=True, help='Skip download phase and create ZIM from existing media')
@click.option('--cleanup', is_flag=True, help='Delete downloaded files after ZIM creation')
@click.option('--dry-run', is_flag=True, help='Simulate operations without downloading')
def archive(urls: List[str], output_dir: str, quality: str, date: Optional[str], 
           date_limit: Optional[int], month_limit: Optional[int], title: Optional[str], 
           description: str, retry_count: int, retry_delay: int, max_retries: int, 
           skip_download: bool, cleanup: bool, dry_run: bool):
    """Download media and create a ZIM archive."""
    archiver = Archiver(output_dir, quality, retry_count, retry_delay, max_retries, dry_run=dry_run)

    if not title:
        title = f"Media_Archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if not skip_download:
        success = True
        results = archiver.download_media(urls, date, date_limit, month_limit)
        for url, result in results.items():
            if not result:
                success = False
                log.error(f"Failed to download: {url}")

        if not success:
            log.warning("Some downloads failed, but continuing with ZIM creation...")
    else:
        log.info("Skipping download phase, creating ZIM from existing media...")

    if archiver.create_zim(title, description):
        log.info("Archive completed successfully")

        if cleanup and not dry_run:
            log.info("Cleaning up downloaded files...")
            archiver.cleanup()
    else:
        log.error("Failed to create archive")
        sys.exit(1)

@cli.command()
@click.option('--config', '-c', default='config.yml', help='Path to configuration file')
def manage(config: str):
    """Run the archive manager in continuous mode."""
    from manager import ArchiveManager
    manager = ArchiveManager(config)
    asyncio.run(manager.run())

if __name__ == '__main__':
    cli() 