#!/usr/bin/env python3

"""
Plex Movie Title Fixer
This script connects to your Plex server and updates movie titles to match their official metadata.
"""

import os
import sys
from plexapi.server import PlexServer
from plexapi.exceptions import NotFound
import argparse
from typing import Optional, Tuple, List
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PlexTitleFixer:
    def __init__(self, base_url: str, token: str, library_name: str):
        """
        Initialize the Plex title fixer.

        Args:
            base_url: The base URL of your Plex server (e.g., 'http://localhost:32400')
            token: Your Plex authentication token
            library_name: The name of your movie library
        """
        self.base_url = base_url
        self.token = token
        self.library_name = library_name
        self.plex = self._connect_to_plex()
        self.library = self._get_library()

    def _connect_to_plex(self) -> PlexServer:
        """Establish connection to Plex server."""
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            return PlexServer(self.base_url, self.token)
        except Exception as e:
            logger.error(f"Failed to connect to Plex server: {e}")
            sys.exit(1)

    def _get_library(self):
        """Get the specified movie library."""
        try:
            return self.plex.library.section(self.library_name)
        except NotFound:
            logger.error(f"Library '{self.library_name}' not found")
            sys.exit(1)

    def get_mismatched_titles(self) -> List[Tuple[str, str, str]]:
        """
        Find all movies where the current title doesn't match the metadata title.

        Returns:
            List of tuples containing (current_title, metadata_title, movie_id)
        """
        mismatched = []

        for movie in self.library.all():
            current_title = movie.title
            metadata_title = movie.originalTitle or movie.title

            if current_title != metadata_title:
                mismatched.append((current_title, metadata_title, movie.ratingKey))

        return mismatched

    def fix_titles(self, dry_run: bool = True) -> None:
        """
        Fix mismatched titles by updating them to match their metadata.

        Args:
            dry_run: If True, only show what would be changed without making changes
        """
        mismatched = self.get_mismatched_titles()

        if not mismatched:
            logger.info("No mismatched titles found!")
            return

        logger.info(f"Found {len(mismatched)} mismatched titles")

        for current, metadata, movie_id in mismatched:
            if dry_run:
                logger.info(f"Would rename: '{current}' -> '{metadata}'")
            else:
                try:
                    movie = self.library.fetchItem(movie_id)
                    movie.edit(**{"title.value": metadata, "title.locked": 1})
                    logger.info(f"Renamed: '{current}' -> '{metadata}'")
                except Exception as e:
                    logger.error(f"Failed to rename '{current}': {e}")

def main():
    parser = argparse.ArgumentParser(description="Fix Plex movie titles to match their metadata")
    parser.add_argument("--url", required=True, help="Plex server URL (e.g., http://localhost:32400)")
    parser.add_argument("--token", required=True, help="Plex authentication token")
    parser.add_argument("--library", required=True, help="Name of the movie library")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")

    args = parser.parse_args()

    fixer = PlexTitleFixer(args.url, args.token, args.library)
    fixer.fix_titles(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
