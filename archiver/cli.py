"""Command line interface for the video archiver."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
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

def handle_error(error: Exception, exit_code: int = 1) -> None:
    """Handle errors with rich formatting."""
    console.print(f"\n[error]Error:[/error] {str(error)}")
    if hasattr(error, '__cause__') and error.__cause__:
        console.print(f"[error]Caused by:[/error] {str(error.__cause__)}")
    sys.exit(exit_code)

def print_header() -> None:
    """Print the application header."""
    console.print(Panel.fit(
        "[bold blue]Video Archiver ZIM[/bold blue]\n"
        "[dim]Download and archive videos from various platforms[/dim]",
        border_style="blue"
    ))

@click.group()
@click.version_option(version="0.2.3", prog_name="Video Archiver ZIM")
def cli():
    """Video archiver CLI."""
    print_header()

@cli.command()
@click.argument('url', required=False)
@click.option('--quality', '-q', default='720p', help='Video quality to download')
@click.option('--title', '-t', help='Title for the video')
@click.option('--description', '-d', help='Description for the video')
@click.option('--output', '-o', type=click.Path(), help='Output directory')
def archive(url: Optional[str], quality: str, title: Optional[str], description: Optional[str], output: Optional[str]):
    """Archive a video from the given URL."""
    try:
        if not url:
            url = Prompt.ask("[info]Enter video URL[/info]")

        if not title:
            title = Prompt.ask("[info]Enter video title[/info]")

        if not description:
            description = Prompt.ask("[info]Enter video description[/info]", default="")

        if not output:
            default_output = str(Path.cwd() / "archive")
            output = Prompt.ask(
                "[info]Enter output directory[/info]",
                default=default_output
            )
            if not Confirm.ask(f"Create directory {output} if it doesn't exist?"):
                handle_error(ValueError("Output directory is required"))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[blue]Archiving video...", total=100)

            archiver = Archiver(output_dir=output, quality=quality)
            results = archiver.download_media([url])

            if all(results.values()):
                if archiver.create_zim(title, description):
                    progress.update(task, completed=100)
                else:
                    handle_error(RuntimeError("Failed to create ZIM archive"))
            else:
                handle_error(RuntimeError("Failed to download video"))

        # Show results
        table = Table(title="Archive Results", show_header=True, header_style="bold blue")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("URL", url)
        table.add_row("Title", title)
        table.add_row("Quality", quality)
        table.add_row("Output Directory", output)

        console.print("\n")
        console.print(table)
        console.print("\n[success]✓ Video archived successfully![/success]")

    except Exception as e:
        handle_error(e)

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