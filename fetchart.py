#!/usr/bin/env python3
"""
fetchart.py - Fetch metadata and artwork for Plex Media Server using TMDB API

Usage:
    fetchart.py [-h] [-r] [-t TARGET_DIR]
    
    -r, --recursive    Process all subdirectories
    -t, --target      Target a specific directory instead of current directory
"""

import os
import argparse
import sys
import requests
import json
from pathlib import Path
import re
import logging
from urllib.parse import quote_plus
from datetime import datetime
from xml.dom import minidom
from xml.etree import ElementTree as ET

class PlexArtFetcher:
    def __init__(self, tmdb_api_key):
        self.tmdb_api_key = tmdb_api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/original"
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Define NFO template paths
        self.movie_nfo_template = '''<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<movie>
    <title>{title}</title>
    <originaltitle>{original_title}</originaltitle>
    <sorttitle>{sort_title}</sorttitle>
    <rating>{rating}</rating>
    <year>{year}</year>
    <plot>{plot}</plot>
    <tagline>{tagline}</tagline>
    <runtime>{runtime}</runtime>
    <thumb aspect="poster" preview="{poster_url}">{poster_url}</thumb>
    <fanart>
        <thumb preview="{backdrop_url}">{backdrop_url}</thumb>
    </fanart>
    {genre_tags}
    <studio>{studio}</studio>
    <id>{tmdb_id}</id>
    <tmdbid>{tmdb_id}</tmdbid>
    {actor_tags}
    {director_tags}
    {writer_tags}
</movie>'''

        self.tvshow_nfo_template = '''<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<tvshow>
    <title>{title}</title>
    <originaltitle>{original_title}</originaltitle>
    <showtitle>{show_title}</showtitle>
    <rating>{rating}</rating>
    <plot>{plot}</plot>
    <runtime>{runtime}</runtime>
    <thumb aspect="poster" preview="{poster_url}">{poster_url}</thumb>
    <fanart>
        <thumb preview="{backdrop_url}">{backdrop_url}</thumb>
    </fanart>
    {genre_tags}
    <studio>{studio}</studio>
    <id>{tmdb_id}</id>
    <tmdbid>{tmdb_id}</tmdbid>
    <premiered>{premiered}</premiered>
    <status>{status}</status>
    {actor_tags}
    {creator_tags}
</tvshow>'''

        self.season_nfo_template = '''<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<season>
    <title>{title}</title>
    <showtitle>{show_title}</showtitle>
    <season>{season_number}</season>
    <plot>{plot}</plot>
    <thumb aspect="poster" preview="{poster_url}">{poster_url}</thumb>
    <premiered>{premiered}</premiered>
</season>'''

    def clean_folder_name(self, folder_name):
        # Extract season number if present
        season_match = re.search(r'S(\d{2})', folder_name, re.IGNORECASE)
        season_number = None
        if season_match:
            season_number = int(season_match.group(1))
            # Remove everything from the season marker onwards
            folder_name = folder_name[:season_match.start()].strip()

        # Find year and ensure it's in parentheses
        year_match = re.search(r'\(?(\d{4})\)?', folder_name)
        year = None
        if year_match:
            year = year_match.group(1)
            # Remove the original year from the string (with or without parentheses)
            folder_name = folder_name[:year_match.start()] + folder_name[year_match.end():]

        # Remove quality tags and other patterns
        cleaned = re.sub(r'720p|1080p|2160p|4K|HDR|REMUX|BluRay|WEB-DL', '', folder_name, flags=re.IGNORECASE)
        cleaned = re.sub(r'[.\-_]', ' ', cleaned)  # Replace separators with spaces
        cleaned = cleaned.strip()

        # Add back the year in parentheses if it exists
        if year:
            cleaned = f"{cleaned} ({year})"

        return cleaned, season_number

    def search_media(self, query, season_number=None):
        # Search both movies and TV shows
        movie_response = self._make_request(f"/search/movie?query={quote_plus(query)}")
        tv_response = self._make_request(f"/search/tv?query={quote_plus(query)}")
        
        movies = movie_response.get('results', [])
        tv_shows = tv_response.get('results', [])
        
        # If we have a season number, prioritize TV shows
        if season_number is not None and tv_shows:
            best_tv = max(tv_shows, key=lambda x: x.get('popularity', 0))
            # Get detailed TV show info
            detailed_tv = self._make_request(f"/tv/{best_tv['id']}")
            # Get season specific information
            season_info = self._make_request(f"/tv/{best_tv['id']}/season/{season_number}")
            if season_info:
                detailed_tv['season_info'] = season_info
            # Get additional images
            detailed_tv['images'] = self._make_request(f"/tv/{best_tv['id']}/images")
            return detailed_tv
        
        # If no season number, get detailed info for most relevant result
        if movies and tv_shows:
            best_movie = max(movies, key=lambda x: x.get('popularity', 0))
            best_tv = max(tv_shows, key=lambda x: x.get('popularity', 0))
            
            if best_movie.get('popularity', 0) > best_tv.get('popularity', 0):
                movie_info = self._make_request(f"/movie/{best_movie['id']}")
                movie_info['images'] = self._make_request(f"/movie/{best_movie['id']}/images")
                return movie_info
            else:
                tv_info = self._make_request(f"/tv/{best_tv['id']}")
                tv_info['images'] = self._make_request(f"/tv/{best_tv['id']}/images")
                return tv_info
        elif movies:
            movie_info = self._make_request(f"/movie/{movies[0]['id']}")
            movie_info['images'] = self._make_request(f"/movie/{movies[0]['id']}/images")
            return movie_info
        elif tv_shows:
            tv_info = self._make_request(f"/tv/{tv_shows[0]['id']}")
            tv_info['images'] = self._make_request(f"/tv/{tv_shows[0]['id']}/images")
            return tv_info
        return None

    def generate_nfo(self, media_info, output_dir, season_number=None):
        """Generate Plex-compatible NFO file."""
        if not media_info:
            return False

        try:
            is_tv = 'seasons' in media_info or 'episode_run_time' in media_info
            
            if is_tv:
                if season_number is not None:
                    # Generate season NFO
                    season_info = media_info.get('season_info', {})
                    nfo_content = self.season_nfo_template.format(
                        title=f"Season {season_number}",
                        show_title=media_info.get('name', ''),
                        season_number=season_number,
                        plot=season_info.get('overview', ''),
                        poster_url=f"{self.image_base_url}{season_info.get('poster_path', '')}",
                        premiered=season_info.get('air_date', '')
                    )
                    nfo_path = os.path.join(output_dir, f"season{season_number:02d}.nfo")
                else:
                    # Generate TV show NFO
                    actor_tags = '\n    '.join(
                        f'<actor><name>{actor["name"]}</name><role>{actor.get("character", "")}</role>'
                        f'<thumb>{self.image_base_url}{actor.get("profile_path", "")}</thumb></actor>'
                        for actor in media_info.get('credits', {}).get('cast', [])[:10]
                    )
                    
                    creator_tags = '\n    '.join(
                        f'<credits>{creator["name"]}</credits>'
                        for creator in media_info.get('created_by', [])
                    )
                    
                    genre_tags = '\n    '.join(
                        f'<genre>{genre["name"]}</genre>'
                        for genre in media_info.get('genres', [])
                    )

                    nfo_content = self.tvshow_nfo_template.format(
                        title=media_info.get('name', ''),
                        original_title=media_info.get('original_name', ''),
                        show_title=media_info.get('name', ''),
                        rating=media_info.get('vote_average', ''),
                        plot=media_info.get('overview', ''),
                        runtime=media_info.get('episode_run_time', [0])[0],
                        poster_url=f"{self.image_base_url}{media_info.get('poster_path', '')}",
                        backdrop_url=f"{self.image_base_url}{media_info.get('backdrop_path', '')}",
                        genre_tags=genre_tags,
                        studio=', '.join(n.get('name', '') for n in media_info.get('networks', [])),
                        tmdb_id=media_info.get('id', ''),
                        premiered=media_info.get('first_air_date', ''),
                        status=media_info.get('status', ''),
                        actor_tags=actor_tags,
                        creator_tags=creator_tags
                    )
                    nfo_path = os.path.join(output_dir, "tvshow.nfo")
            else:
                # Generate movie NFO
                credits_info = media_info.get('credits', {})
                
                actor_tags = '\n    '.join(
                    f'<actor><name>{actor["name"]}</name><role>{actor.get("character", "")}</role>'
                    f'<thumb>{self.image_base_url}{actor.get("profile_path", "")}</thumb></actor>'
                    for actor in credits_info.get('cast', [])[:10]
                )
                
                director_tags = '\n    '.join(
                    f'<director>{crew["name"]}</director>'
                    for crew in credits_info.get('crew', [])
                    if crew.get('job') == 'Director'
                )
                
                writer_tags = '\n    '.join(
                    f'<credits>{crew["name"]}</credits>'
                    for crew in credits_info.get('crew', [])
                    if crew.get('job') in ['Screenplay', 'Writer']
                )
                
                genre_tags = '\n    '.join(
                    f'<genre>{genre["name"]}</genre>'
                    for genre in media_info.get('genres', [])
                )

                nfo_content = self.movie_nfo_template.format(
                    title=media_info.get('title', ''),
                    original_title=media_info.get('original_title', ''),
                    sort_title=media_info.get('title', ''),
                    rating=media_info.get('vote_average', ''),
                    year=media_info.get('release_date', '')[:4],
                    plot=media_info.get('overview', ''),
                    tagline=media_info.get('tagline', ''),
                    runtime=media_info.get('runtime', ''),
                    poster_url=f"{self.image_base_url}{media_info.get('poster_path', '')}",
                    backdrop_url=f"{self.image_base_url}{media_info.get('backdrop_path', '')}",
                    genre_tags=genre_tags,
                    studio=', '.join(c.get('name', '') for c in media_info.get('production_companies', [])),
                    tmdb_id=media_info.get('id', ''),
                    actor_tags=actor_tags,
                    director_tags=director_tags,
                    writer_tags=writer_tags
                )
                nfo_path = os.path.join(output_dir, f"{media_info['title']}.nfo")

            # Write the NFO file
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(nfo_content)
            
            self.logger.info(f"Successfully generated NFO file: {nfo_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate NFO file: {str(e)}")
            return False

    def cleanup_existing_assets(self, directory):
        """Remove existing art assets and NFO files."""
        try:
            # Define patterns for files to remove
            art_patterns = [
                'poster.jpg',
                'background.jpg',
                'banner.jpg',
                'logo.png',
                'season*.jpg',  # Matches season posters and banners
                '*.nfo',        # Matches all NFO files
            ]
            
            # Remove files in main directory
            for pattern in art_patterns:
                for file in Path(directory).glob(pattern):
                    self.logger.info(f"Removing existing file: {file}")
                    file.unlink()
            
            # Clean up .artwork directory if it exists
            artwork_dir = Path(directory) / '.artwork'
            if artwork_dir.exists():
                self.logger.info("Cleaning up .artwork directory")
                for file in artwork_dir.glob('*'):
                    file.unlink()
                # Remove the empty directory
                artwork_dir.rmdir()
                
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up existing assets: {str(e)}")
            return False

    def download_plex_artwork(self, media_info, output_dir):
        """Download all relevant artwork for Plex Media Server."""
        if not media_info:
            return False

        is_tv = 'seasons' in media_info or 'episode_run_time' in media_info
        images = media_info.get('images', {})
        season_info = media_info.get('season_info', {})
        
        # Create artwork directory for extras
        art_dir = Path(output_dir) / '.artwork'
        art_dir.mkdir(exist_ok=True)
        
        success = True
        
        # Download primary poster
        poster_path = season_info.get('poster_path') if is_tv and season_info else media_info.get('poster_path')
        if poster_path:
            success &= self._save_image(poster_path, output_dir, 'poster.jpg')
        
        # Download backdrop/fanart (use first backdrop)
        backdrops = images.get('backdrops', [])
        if backdrops:
            success &= self._save_image(backdrops[0]['file_path'], output_dir, 'background.jpg')
            # Save additional backdrops in .artwork directory
            for i, backdrop in enumerate(backdrops[1:], 1):
                success &= self._save_image(backdrop['file_path'], art_dir, f'background-{i}.jpg')
        
        # For TV shows, handle season-specific artwork
        if is_tv and season_info:
            season_number = season_info.get('season_number')
            if season_number is not None:
                # Season poster
                if season_info.get('poster_path'):
                    success &= self._save_image(
                        season_info['poster_path'],
                        output_dir,
                        f'season{season_number:02d}-poster.jpg'
                    )
                
                # Season banner if available
                if images.get('season_banners'):
                    banner = next((b for b in images['season_banners'] if b.get('season_number') == season_number), None)
                    if banner:
                        success &= self._save_image(
                            banner['file_path'],
                            output_dir,
                            f'season{season_number:02d}-banner.jpg'
                        )
        
        # Download logo if available
        logos = images.get('logos', [])
        if logos:
            success &= self._save_image(logos[0]['file_path'], output_dir, 'logo.png')
        
        # Download banner if available
        if images.get('banners'):
            success &= self._save_image(images['banners'][0]['file_path'], output_dir, 'banner.jpg')
        
        # Download clearart if available (typically for movies)
        if not is_tv and images.get('clearart'):
            success &= self._save_image(images['clearart'][0]['file_path'], art_dir, 'clearart.png')
        
        return success

    def _save_image(self, image_path, output_dir, filename):
        """Download and save an image from TMDB."""
        try:
            image_url = f"{self.image_base_url}{image_path}"
            response = requests.get(image_url)
            
            if response.status_code == 200:
                output_path = Path(output_dir) / filename
                output_path.write_bytes(response.content)
                self.logger.info(f"Successfully saved {filename}")
                return True
            else:
                self.logger.warning(f"Failed to download {filename}: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving {filename}: {str(e)}")
            return False

    def _make_request(self, endpoint):
        separator = '?' if '?' not in endpoint else '&'
        url = f"{self.base_url}{endpoint}{separator}api_key={self.tmdb_api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None

def process_directory(fetcher, directory):
    """Process a single directory for media metadata."""
    # Get folder name
    folder_name = os.path.basename(directory)
    
    # Clean the folder name and get season number if present
    cleaned_name, season_number = fetcher.clean_folder_name(folder_name)
    
    fetcher.logger.info(f"Processing directory: {directory}")
    fetcher.logger.info(f"Searching for: {cleaned_name}")
    if season_number:
        fetcher.logger.info(f"Season number detected: {season_number}")
    
    # Search for media
    media_info = fetcher.search_media(cleaned_name, season_number)
    
    if media_info:
        title = media_info.get('title') or media_info.get('name')
        if season_number:
            title = f"{title} - Season {season_number}"
        fetcher.logger.info(f"Found media: {title}")
        
        # Clean up existing assets first
        if not fetcher.cleanup_existing_assets(directory):
            fetcher.logger.warning("Failed to clean up some existing assets")
        
        # Generate NFO file
        if fetcher.generate_nfo(media_info, directory, season_number):
            fetcher.logger.info("Successfully generated NFO file")
        else:
            fetcher.logger.error("Failed to generate NFO file")

        # Download all relevant artwork
        if fetcher.download_plex_artwork(media_info, directory):
            fetcher.logger.info("Successfully downloaded artwork")
        else:
            fetcher.logger.error("Failed to download some artwork")
    else:
        fetcher.logger.error("No media information found")

def should_process_directory(directory):
    """Determine if a directory should be processed based on its contents."""
    # Skip directories that start with a dot
    if os.path.basename(directory).startswith('.'):
        return False
        
    # Check if directory contains video files
    video_extensions = {'.mkv', '.mp4', '.avi', '.m4v', '.wmv', '.mov'}
    for file in os.listdir(directory):
        if any(file.lower().endswith(ext) for ext in video_extensions):
            return True
    return False

def get_api_key():
    """Read TMDB API key from config file."""
    config_path = os.path.expanduser("~/.config/fetchart/config")
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Try to read the API key
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                api_key = f.read().strip()
                if api_key:
                    return api_key
                
        # If we get here, either the file doesn't exist or is empty
        logging.error("TMDB API key not found in ~/.config/fetchart/config")
        logging.error("Please create the file and add your API key")
        sys.exit(1)
        
    except Exception as e:
        logging.error(f"Error reading API key: {str(e)}")
        sys.exit(1)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Fetch artwork for Plex Media Server.')
    parser.add_argument('-r', '--recursive', action='store_true', 
                        help='Process all subdirectories recursively')
    parser.add_argument('-t', '--target', type=str,
                        help='Target a specific directory instead of current directory')
    args = parser.parse_args()
    
    # Get API key from config file
    TMDB_API_KEY = get_api_key()
    
    # Initialize the fetcher
    fetcher = PlexArtFetcher(TMDB_API_KEY)
    
    # Determine the root directory to start from
    root_dir = args.target if args.target else os.getcwd()
    
    if not os.path.isdir(root_dir):
        fetcher.logger.error(f"Directory not found: {root_dir}")
        return
    
    if args.recursive:
        # Walk through all subdirectories
        for dirpath, dirnames, _ in os.walk(root_dir):
            # Skip hidden directories
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
            
            if should_process_directory(dirpath):
                process_directory(fetcher, dirpath)
    else:
        # Process single directory
        if should_process_directory(root_dir):
            process_directory(fetcher, root_dir)

if __name__ == "__main__":
    main()