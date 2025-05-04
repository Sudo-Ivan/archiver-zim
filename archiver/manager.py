"""Manager module for handling continuous ZIM archive updates."""

# Copyright (c) 2025 Sudo-Ivan
# Licensed under the MIT License (see LICENSE file for details)

import yaml
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
from archiver import Archiver, OutputFilter
from rich.logging import RichHandler

class ArchiveManager:
    """Manages continuous running and updates of ZIM archives based on configuration."""

    def __init__(self, config_path: str):
        """
        Initialize the ArchiveManager.

        Args:
            config_path: Path to the configuration YAML file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.archives: Dict[str, Dict[str, Any]] = {}
        self.last_updates: Dict[str, datetime] = {}
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging for the manager."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[
                RichHandler(rich_tracebacks=False, markup=True, show_time=False),
                logging.FileHandler("archive_manager.log", mode='a')
            ]
        )
        self.logger = logging.getLogger("ArchiveManager")
        self.logger.addFilter(OutputFilter())  # Reuse the same filter from archiver.py

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Dict containing configuration settings
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Validate required fields
        required_fields = ['archives']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in configuration")

        # Validate each archive configuration
        for archive_id, archive_config in config['archives'].items():
            if 'urls' not in archive_config:
                raise ValueError(f"Missing 'urls' field in archive '{archive_id}'")
            if not isinstance(archive_config['urls'], list):
                raise ValueError(f"'urls' field in archive '{archive_id}' must be a list")

            # Set default values for optional fields
            archive_config.setdefault('update_interval', 24)  # hours
            archive_config.setdefault('quality', 'best')
            archive_config.setdefault('retry_count', 3)
            archive_config.setdefault('retry_delay', 5)
            archive_config.setdefault('max_retries', 10)
            archive_config.setdefault('max_concurrent_downloads', 3)
            archive_config.setdefault('cleanup', False)
            archive_config.setdefault('cookies', None)
            archive_config.setdefault('cookies_from_browser', None)

        return config

    @staticmethod
    def _parse_frequency(frequency: str) -> timedelta:
        """
        Parse update frequency string into timedelta.

        Args:
            frequency: String in format "Nd" (days), "Nw" (weeks), "Nm" (months), "Ny" (years)

        Returns:
            timedelta object representing the frequency
        """
        value = int(frequency[:-1])
        unit = frequency[-1].lower()

        if unit == 'd':
            return timedelta(days=value)
        elif unit == 'w':
            return timedelta(weeks=value)
        elif unit == 'm':
            return timedelta(days=value * 30)
        elif unit == 'y':
            return timedelta(days=value * 365)
        else:
            raise ValueError(f"Invalid frequency unit: {unit}")

    def _should_update(self, archive_name: str) -> bool:
        """
        Check if an archive should be updated based on its frequency.

        Args:
            archive_name: Name of the archive to check

        Returns:
            True if the archive should be updated, False otherwise
        """
        if archive_name not in self.last_updates:
            return True

        archive_config = next(
            (a for a in self.config['archives'] if a['name'] == archive_name),
            None
        )
        if not archive_config:
            return False

        frequency = self._parse_frequency(archive_config['update_frequency'])
        last_update = self.last_updates[archive_name]
        return datetime.now() - last_update >= frequency

    async def _process_archive(self, archive_id: str, archive_config: Dict[str, Any]):
        """
        Process a single archive configuration.

        Args:
            archive_id: Unique identifier for the archive
            archive_config: Archive configuration dictionary
        """
        try:
            # Check if it's time to update
            last_update = self.last_updates.get(archive_id)
            if last_update:
                time_since_update = datetime.now() - last_update
                if time_since_update < timedelta(hours=archive_config['update_interval']):
                    self.logger.info(f"[yellow]Skipping {archive_id} - Last update was {time_since_update.total_seconds() / 3600:.1f} hours ago[/yellow]")
                    return

            self.logger.info(f"[green]Processing archive: {archive_id}[/green]")

            # Create output directory
            output_dir = Path(f"archives/{archive_id}")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Initialize archiver with configuration
            archiver = Archiver(
                str(output_dir),
                quality=archive_config['quality'],
                retry_count=archive_config['retry_count'],
                retry_delay=archive_config['retry_delay'],
                max_retries=archive_config['max_retries'],
                max_concurrent_downloads=archive_config['max_concurrent_downloads'],
                cookies=archive_config['cookies'],
                cookies_from_browser=archive_config['cookies_from_browser']
            )

            # Process URLs
            for url in archive_config['urls']:
                try:
                    await archiver.process_url(url)
                except Exception as e:
                    self.logger.error(f"[red]Error processing URL {url}: {str(e)}[/red]")

            # Update last update time
            self.last_updates[archive_id] = datetime.now()
            self.logger.info(f"[green]Completed archive: {archive_id}[/green]")

        except Exception as e:
            self.logger.error(f"[red]Error processing archive {archive_id}: {str(e)}[/red]")

    async def run(self):
        """Run the archive manager continuously."""
        self.logger.info("Starting Archive Manager")

        while True:
            try:
                self.config = self._load_config()  # Reload config to pick up changes

                tasks = []
                for archive_id, archive_config in self.config['archives'].items():
                    tasks.append(self._process_archive(archive_id, archive_config))

                await asyncio.gather(*tasks)

                # Sleep for 1 hour before next check
                await asyncio.sleep(3600)

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(300)  # Sleep for 5 minutes on error

def main():
    """Main entry point for the archive manager."""
    manager = ArchiveManager("config.yml")
    asyncio.run(manager.run())

if __name__ == "__main__":
    main() 