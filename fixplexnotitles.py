#!/usr/bin/env python3

import os
from plexapi.server import PlexServer
from plexapi.exceptions import NotFound, BadRequest
import logging
from typing import Optional, List, Dict
import argparse
import time
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PlexTitleFixer:
    def __init__(self, base_url: str, token: str, library_name: Optional[str] = None, 
                 dry_run: bool = False, force_refresh: bool = False):
        """
        Initialize the PlexTitleFixer with server connection details.
        
        Args:
            base_url: The URL of your Plex server (e.g., 'http://localhost:32400')
            token: Your Plex authentication token
            library_name: Optional name of specific library to process
            dry_run: If True, only show what would be done without making changes
            force_refresh: If True, force refresh metadata even if original title exists
        """
        self.plex = PlexServer(base_url, token)
        self.library_name = library_name
        self.dry_run = dry_run
        self.force_refresh = force_refresh
        self.stats = {
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

    def get_libraries(self) -> List[str]:
        """Get all movie and TV show libraries."""
        return [
            section.title for section in self.plex.library.sections()
            if section.type in ('movie', 'show')
        ]

    def needs_update(self, item) -> bool:
        """
        Check if an item needs its title updated.
        
        Args:
            item: PlexAPI media item
        Returns:
            bool: True if item needs update
        """
        if self.force_refresh:
            return True

        # Check for missing or empty original title
        if not hasattr(item, 'originalTitle') or not item.originalTitle:
            return True

        # Check for title mismatch with external agents
        if hasattr(item, 'guid'):
            if ('themoviedb://' in item.guid or 
                'imdb://' in item.guid or 
                'tvdb://' in item.guid):
                # Check if title matches between Plex and external metadata
                # This could be expanded based on your specific needs
                return True

        # Check for non-ASCII characters in title but not in originalTitle
        if any(ord(c) > 127 for c in item.title):
            if not item.originalTitle or not any(ord(c) > 127 for c in item.originalTitle):
                return True

        return False

    def process_library(self, library_name: str) -> None:
        """
        Process all items in a given library.
        
        Args:
            library_name: Name of the library to process
        """
        try:
            library = self.plex.library.section(library_name)
            logger.info(f"Processing library: {library_name}")
            
            # Get all items in the library
            items = library.all()
            total_items = len(items)
            
            for idx, item in enumerate(items, 1):
                logger.info(f"Processing item {idx}/{total_items}: {item.title}")
                self.process_item(item)
                
        except NotFound:
            logger.error(f"Library '{library_name}' not found")
            self.stats['errors'] += 1
        except Exception as e:
            logger.error(f"Error processing library '{library_name}': {str(e)}")
            self.stats['errors'] += 1

    def process_item(self, item) -> None:
        """
        Process a single item (movie or TV show).
        
        Args:
            item: PlexAPI media item
        """
        try:
            self.stats['processed'] += 1
            
            if not self.needs_update(item):
                logger.debug(f"Skipping {item.title} - no update needed")
                self.stats['skipped'] += 1
                return

            # Log current state
            current_state = {
                'title': item.title,
                'originalTitle': getattr(item, 'originalTitle', None),
                'guid': getattr(item, 'guid', None)
            }
            
            logger.info(f"Current state: {current_state}")

            if self.dry_run:
                logger.info(f"[DRY RUN] Would update: {item.title}")
                self.stats['updated'] += 1
                return

            # For TV shows, handle series and episodes
            if item.type == 'show':
                self.fix_show_title(item)
            else:
                self.fix_movie_title(item)

            # Wait a bit to avoid overwhelming the server
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error processing item '{item.title}': {str(e)}")
            self.stats['errors'] += 1

    def fix_movie_title(self, movie) -> None:
        """
        Fix original title for a movie.
        
        Args:
            movie: PlexAPI movie object
        """
        try:
            # Force metadata refresh and match
            movie.refresh()
            time.sleep(2)  # Give time for initial refresh
            
            # Try to match against external agents
            try:
                movie.matchAgents()
                self.stats['updated'] += 1
                logger.info(f"Updated movie: {movie.title}")
            except BadRequest:
                # If match fails, try alternative matching
                logger.warning(f"Initial match failed for {movie.title}, trying alternative match")
                movie.fixMatch()
            
            # Final refresh to ensure changes are applied
            movie.refresh()
            
        except Exception as e:
            logger.error(f"Error fixing movie '{movie.title}': {str(e)}")
            self.stats['errors'] += 1

    def fix_show_title(self, show) -> None:
        """
        Fix original title for a TV show.
        
        Args:
            show: PlexAPI show object
        """
        try:
            # First fix the show-level metadata
            show.refresh()
            time.sleep(2)  # Give time for initial refresh
            
            try:
                show.matchAgents()
                self.stats['updated'] += 1
                logger.info(f"Updated show: {show.title}")
            except BadRequest:
                logger.warning(f"Initial match failed for {show.title}, trying alternative match")
                show.fixMatch()
            
            # Then handle episodes if needed
            if self.force_refresh:
                for season in show.seasons():
                    for episode in season.episodes():
                        if self.needs_update(episode):
                            episode.refresh()
                            time.sleep(1)  # Avoid overwhelming the server
            
            # Final refresh to ensure changes are applied
            show.refresh()
            
        except Exception as e:
            logger.error(f"Error fixing show '{show.title}': {str(e)}")
            self.stats['errors'] += 1

    def print_stats(self) -> None:
        """Print statistics about the run."""
        logger.info("\nRun Statistics:")
        logger.info(f"Total items processed: {self.stats['processed']}")
        logger.info(f"Items updated: {self.stats['updated']}")
        logger.info(f"Items skipped: {self.stats['skipped']}")
        logger.info(f"Errors encountered: {self.stats['errors']}")

    def run(self) -> None:
        """Main execution method."""
        start_time = datetime.now()
        logger.info(f"Starting title fix run at {start_time}")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info(f"Force refresh: {self.force_refresh}")

        if self.library_name:
            self.process_library(self.library_name)
        else:
            libraries = self.get_libraries()
            for library in libraries:
                self.process_library(library)

        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"\nRun completed at {end_time}")
        logger.info(f"Total duration: {duration}")
        self.print_stats()

def main():
    parser = argparse.ArgumentParser(description='Fix missing original titles in Plex libraries')
    parser.add_argument('--url', required=True, help='Plex server URL (e.g., http://localhost:32400)')
    parser.add_argument('--token', required=True, help='Plex authentication token')
    parser.add_argument('--library', help='Specific library to process (optional)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--force-refresh', action='store_true', 
                       help='Force refresh metadata even if original title exists')
    
    args = parser.parse_args()
    
    fixer = PlexTitleFixer(
        args.url, 
        args.token, 
        args.library, 
        args.dry_run,
        args.force_refresh
    )
    fixer.run()

if __name__ == '__main__':
    main()