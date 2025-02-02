#!/usr/bin/env python3

import os
import re
from pathlib import Path
from typing import List, Set
import subprocess
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'video_metadata_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

# Video file extensions to process
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv'}
# Base directories to search
BASE_DIRS = ['/data/media/Movies', '/data/media/Shows']

def is_video_file(file_path: Path) -> bool:
    """Check if the file has a video extension."""
    return file_path.suffix.lower() in VIDEO_EXTENSIONS

def extract_title(directory_name: str) -> str:
    """
    Extract title by removing parentheses but keeping the year.
    
    Args:
        directory_name: The name of the directory containing the video
        
    Returns:
        Clean title with parentheses removed but year retained
    """
    # First decode URL encoding (e.g., %20 to space)
    from urllib.parse import unquote
    decoded_name = unquote(directory_name)
    
    # Pattern matches parentheses while capturing the year inside
    parens_pattern = r'\s*\((\d{4})\)'
    
    # Remove parentheses but keep the year, then strip any extra whitespace
    clean_title = re.sub(parens_pattern, r' \1', decoded_name).strip()
    
    return clean_title

def get_first_subdir(file_path: Path, base_dir: str) -> str:
    """Get the first subdirectory name under the base directory."""
    try:
        # Get the relative path from base_dir
        rel_path = file_path.relative_to(Path(base_dir))
        # Return the first part of the path
        return rel_path.parts[0]
    except ValueError:
        return ""

def extract_episode_info(file_path: Path) -> tuple[str, str, str]:
    """
    Extract season, episode numbers, and episode title from filename.
    Returns tuple of (season_num, episode_num, episode_title).
    """
    filename = file_path.stem
    season_num = ""
    episode_num = ""
    episode_title = ""

    # Extract season and episode numbers first
    se_pattern = r'[Ss](\d{1,2})[Ee](\d{1,2})'
    alt_pattern = r'(\d{1,2})x(\d{1,2})'
    
    # Try S01E01 pattern first
    match = re.search(se_pattern, filename)
    if match:
        season_num = str(int(match.group(1))).zfill(2)
        episode_num = str(int(match.group(2))).zfill(2)
    else:
        # Try 1x01 pattern
        match = re.search(alt_pattern, filename)
        if match:
            season_num = str(int(match.group(1))).zfill(2)
            episode_num = str(int(match.group(2))).zfill(2)
    
    # Extract episode title
    parts = filename.split(" - ")
    if len(parts) > 2:  # Format like "Show - S01E01 - Title"
        episode_title = parts[-1].strip()
    
    return season_num, episode_num, episode_title

def format_show_title(show_name: str, season: str, episode: str, episode_title: str = "") -> str:
    """Format show title with episode information and episode title if available."""
    base = show_name
    if season and episode:
        base = f"{base} S{season}E{episode}"
    elif episode:
        base = f"{base} E{episode}"
    
    if episode_title:
        base = f"{base} - {episode_title}"
    
    return base

def update_video_metadata(file_path: Path, title: str) -> bool:
    """
    Update the video file's title metadata using ffmpeg.
    Returns True if successful, False otherwise.
    """
    temp_file = file_path.parent / f"temp_{file_path.name}"
    
    try:
        # Build ffmpeg command based on file extension
        if file_path.suffix.lower() in {'.mp4', '.m4v'}:
            cmd = [
                'ffmpeg', '-i', str(file_path),
                '-metadata', f'title={title}',
                '-codec', 'copy',
                str(temp_file)
            ]
        else:
            # For other formats, we'll need to modify the command accordingly
            cmd = [
                'ffmpeg', '-i', str(file_path),
                '-metadata', f'title={title}',
                '-c', 'copy',
                str(temp_file)
            ]

        # Execute ffmpeg command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Replace original file with the new one
            os.replace(temp_file, file_path)
            logging.info(f"Successfully updated metadata for: {file_path}")
            return True
        else:
            logging.error(f"Failed to update metadata for {file_path}: {result.stderr}")
            if temp_file.exists():
                temp_file.unlink()
            return False
            
    except Exception as e:
        logging.error(f"Error processing {file_path}: {str(e)}")
        if temp_file.exists():
            temp_file.unlink()
        return False

def process_videos(dry_run: bool = True) -> None:
    """
    Main function to walk directories and process video files.
    
    Args:
        dry_run: If True, only log what would be done without making changes
    """
    for base_dir in BASE_DIRS:
        base_path = Path(base_dir)
        
        if not base_path.exists():
            logging.warning(f"Base directory does not exist: {base_dir}")
            continue
            
        logging.info(f"Processing directory: {base_dir}")
        is_shows = "Shows" in base_path.parts
        
        # Walk through the directory
        for root, _, files in os.walk(base_dir):
            root_path = Path(root)
            
            # Process each file
            for file in files:
                file_path = root_path / file
                
                if not is_video_file(file_path):
                    continue
                
                # Get the first subdirectory name
                subdir = get_first_subdir(file_path, base_dir)
                if not subdir:
                    continue
                
                # Extract base title from directory name
                base_title = extract_title(subdir)
                
                # For TV shows, try to extract episode information
                if is_shows:
                    season_num, episode_num, episode_title = extract_episode_info(file_path)
                    title = format_show_title(base_title, season_num, episode_num, episode_title)
                else:
                    title = base_title
                
                logging.info(f"Processing file: {file_path}")
                logging.info(f"Extracted title: {title}")
                
                if dry_run:
                    logging.info(f"[DRY RUN] Would update metadata title to: {title}")
                else:
                    # Update the metadata
                    update_video_metadata(file_path, title)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Update video metadata titles based on directory names.')
    parser.add_argument('--execute', action='store_true',
                      help='Execute the changes. Without this flag, runs in dry-run mode.')
    
    args = parser.parse_args()
    
    try:
        process_videos(dry_run=not args.execute)
        logging.info("Video processing completed")
    except Exception as e:
        logging.error(f"An error occurred during processing: {str(e)}")