"""Command line interface for the Archiver ZIM."""

import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import logging

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.theme import Theme

from .archiver import Archiver

# Custom theme for rich
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "success": "green",
    "progress": "blue",
})

console = Console(theme=custom_theme)

log = logging.getLogger(__name__)

def handle_error(error: Exception, exit_code: int = 1) -> None:
    """Handle errors with rich formatting."""
    console.print(f"\n[error]Error:[/error] {str(error)}")
    if hasattr(error, '__cause__') and error.__cause__:
        console.print(f"[error]Caused by:[/error] {str(error.__cause__)}")
    sys.exit(exit_code)

def print_header() -> None:
    """Print the application header."""
    console.print(Panel.fit(
        "[bold blue]Archiver ZIM[/bold blue]\n"
        "[dim]Download and archive videos and podcasts from various platforms[/dim]",
        border_style="blue"
    ))

@click.group()
@click.version_option(version="0.3.3", prog_name="Archiver ZIM")
def cli():
    """Archiver ZIM CLI."""
    print_header()

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
@click.option('--max-concurrent-downloads', default=3, help='Maximum number of concurrent downloads')
@click.option('--skip-download', is_flag=True, help='Skip download phase and create ZIM from existing media')
@click.option('--cleanup', is_flag=True, help='Delete downloaded files after ZIM creation')
@click.option('--dry-run', is_flag=True, help='Simulate operations without downloading')
@click.option('--cookies', help='Path to cookies file')
@click.option('--cookies-from-browser', help='Browser to extract cookies from (e.g., firefox, chrome)')
def archive(urls: List[str], output_dir: str, quality: str, date: Optional[str], 
           date_limit: Optional[int], month_limit: Optional[int], title: Optional[str], 
           description: str, retry_count: int, retry_delay: int, max_retries: int,
           max_concurrent_downloads: int, skip_download: bool, cleanup: bool, dry_run: bool, 
           cookies: Optional[str], cookies_from_browser: Optional[str]):
    """Download media and create a ZIM archive.

    Supports both video and podcast content:
    - Videos: YouTube, Vimeo, etc.
    - Podcasts: RSS feeds (.xml, .atom, .json, .rss)

    Examples:
        # Download a video
        archiver-zim archive "https://www.youtube.com/watch?v=VIDEO_ID" --quality 720p

        # Download a podcast feed
        archiver-zim archive "https://example.com/feed.xml" --date-limit 30

        # Download multiple items
        archiver-zim archive "https://youtube.com/..." "https://example.com/feed.xml"
    """
    archiver = Archiver(output_dir, quality, retry_count, retry_delay, max_retries, 
                       max_concurrent_downloads=max_concurrent_downloads,
                       dry_run=dry_run, cookies=cookies, cookies_from_browser=cookies_from_browser)

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
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
@click.option('--watch-dir', '-w', type=click.Path(), help='Directory to watch for new videos')
def manage(config: Optional[str], watch_dir: Optional[str]):
    """Run in continuous mode."""
    try:
        if not config:
            default_config = str(Path.cwd() / "config" / "config.yaml")
            config = Prompt.ask(
                "[info]Enter configuration file path[/info]",
                default=default_config
            )

        if not watch_dir:
            default_watch = str(Path.cwd() / "watch")
            watch_dir = Prompt.ask(
                "[info]Enter watch directory[/info]",
                default=default_watch
            )
            if not Confirm.ask(f"Create directory {watch_dir} if it doesn't exist?"):
                handle_error(ValueError("Watch directory is required"))

        console.print("\n[info]Starting manager in continuous mode...[/info]")
        console.print(f"[dim]Config: {config}[/dim]")
        console.print(f"[dim]Watch Directory: {watch_dir}[/dim]\n")

        from .manager import ArchiveManager
        manager = ArchiveManager(config)
        manager.run()

    except Exception as e:
        handle_error(e)

def main():
    """Main entry point."""
    try:
        cli()
    except Exception as e:
        handle_error(e) 