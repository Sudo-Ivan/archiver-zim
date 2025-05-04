"""Manager module for handling continuous ZIM archive updates."""

# Copyright (c) 2025 Sudo-Ivan
# Licensed under the MIT License (see LICENSE file for details)

import yaml
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
from archiver import Archiver

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
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("archive_manager.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("ArchiveManager")

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Dict containing the configuration
        """
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")

    def _parse_frequency(self, frequency: str) -> timedelta:
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

    async def _process_archive(self, archive_config: Dict[str, Any]):
        """
        Process a single archive configuration.

        Args:
            archive_config: Archive configuration dictionary
        """
        archive_name = archive_config['name']
        if not self._should_update(archive_name):
            self.logger.info(f"Skipping {archive_name} - not due for update")
            return

        self.logger.info(f"Processing archive: {archive_name}")

        output_dir = Path(self.config['settings']['output_base_dir']) / archive_name
        output_dir.mkdir(parents=True, exist_ok=True)

        archiver = Archiver(
            output_dir=str(output_dir),
            quality=archive_config.get('quality', self.config['settings']['quality']),
            retry_count=self.config['settings']['retry_count'],
            retry_delay=self.config['settings']['retry_delay'],
            max_retries=self.config['settings']['max_retries'],
            max_concurrent_downloads=self.config['settings']['max_concurrent_downloads']
        )

        try:
            if archive_config['type'] == 'mixed':
                urls = [source['url'] for source in archive_config['sources']]
            else:
                urls = [archive_config['url']]

            date_limit = archive_config.get('date_limit')
            month_limit = archive_config.get('month_limit')

            results = await archiver.download_media_async(
                urls=urls,
                date_limit=date_limit,
                month_limit=month_limit
            )

            if all(results.values()):
                if archiver.create_zim(
                    title=archive_name,
                    description=archive_config.get('description', '')
                ):
                    self.last_updates[archive_name] = datetime.now()
                    if self.config['settings']['cleanup_after_archive']:
                        archiver.cleanup()
                    self.logger.info(f"Successfully updated archive: {archive_name}")
                else:
                    self.logger.error(f"Failed to create ZIM for archive: {archive_name}")
            else:
                self.logger.error(f"Some downloads failed for archive: {archive_name}")

        except Exception as e:
            self.logger.error(f"Error processing archive {archive_name}: {e}")

    async def run(self):
        """Run the archive manager continuously."""
        self.logger.info("Starting Archive Manager")

        while True:
            try:
                self.config = self._load_config()  # Reload config to pick up changes

                tasks = []
                for archive_config in self.config['archives']:
                    tasks.append(self._process_archive(archive_config))

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