#!/usr/bin/env python3

import os
import shutil
from pathlib import Path
import argparse
from mutagen.easyid3 import EasyID3
import re
from tqdm import tqdm

def sanitize_path_component(name, is_artist=False):
    """
    Sanitize a path component (file or directory name) while preserving as much of the original as possible.
    Only replaces characters that are actually invalid for the filesystem.
    
    Args:
        name (str): Original name from ID3 tag
        is_artist (bool): Whether this is an artist name (to preserve special formatting)
    Returns:
        str: Sanitized name safe for filesystem use
    """
    if not name:
        return "Unknown"
    
    result = name
    
    # For artist names, we only replace strictly invalid filesystem characters
    # while preserving everything else exactly as it appears in the ID3 tag
    if is_artist:
        # Only replace characters that are strictly invalid in filesystems
        invalid_chars = '<>:|?*\0'
        for char in invalid_chars:
            result = result.replace(char, '_')
    else:
        # For non-artist names, use more thorough sanitization
        replacements = {
            ':': ' -',
            '/': '⁄',
            '\\': '⁄',
            '|': 'ǀ',
            '*': '∗',
            '?': '？',
            '"': '"',
            '<': '‹',
            '>': '›',
            '\0': ''
        }
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)
    
    # Remove leading/trailing periods and spaces (invalid in Windows)
    result = result.strip('. ')
    
    # If name would be empty after sanitization, provide a fallback
    if not result:
        return "Unknown"
        
    return result

def organize_mp3s(source_dir, target_dir, dry_run=True):
    """
    Organize MP3 files into artist/album directory structure.
    
    Args:
        source_dir (str): Directory containing MP3 files
        target_dir (str): Base directory for organized files
        dry_run (bool): If True, only print actions without moving files
    """
    source_path = Path(source_dir)
    target_path = Path(target_dir)
    
    # Track files that would be overwritten
    potential_conflicts = []
    
    # Store all planned moves to detect collisions
    planned_moves = {}
    
    print(f"{'DRY RUN: ' if dry_run else ''}Scanning directory: {source_dir}")
    
    # Get list of all MP3 files first
    mp3_files = list(source_path.rglob("*.mp3"))
    total_files = len(mp3_files)
    
    if total_files == 0:
        print("No MP3 files found in the source directory.")
        return
    
    # Track original vs sanitized names for reporting
    name_changes = []
    
    # First pass: collect all planned moves and check for conflicts
    print("\nAnalyzing files and planning moves:")
    for mp3_file in tqdm(mp3_files, desc="Planning", unit="file"):
        try:
            tags = EasyID3(mp3_file)
            
            # Get original tag values
            original_artist = tags.get('artist', ['Unknown Artist'])[0]
            original_album = tags.get('album', ['Unknown Album'])[0]
            
            # Sanitize for filesystem
            artist = sanitize_path_component(original_artist, is_artist=True)
            album = sanitize_path_component(original_album, is_artist=False)
            
            # Track if names were changed during sanitization
            if artist != original_artist:
                name_changes.append(('Artist', original_artist, artist))
            if album != original_album:
                name_changes.append(('Album', original_album, album))
            
            # Create target directory structure
            artist_dir = target_path / artist
            album_dir = artist_dir / album
            
            # Generate target filepath
            target_file = album_dir / mp3_file.name
            
            # Store planned move
            if target_file in planned_moves:
                potential_conflicts.append((mp3_file, target_file))
            planned_moves[target_file] = mp3_file
            
        except Exception as e:
            print(f"\nError processing {mp3_file}: {str(e)}")
            continue
    
    # Report any name changes due to sanitization
    if name_changes and dry_run:
        print("\nThe following names needed to be sanitized for filesystem compatibility:")
        for tag_type, original, sanitized in name_changes:
            print(f"{tag_type}: '{original}' → '{sanitized}'")
    
    # Second pass: execute moves
    print(f"\n{'Would execute' if dry_run else 'Executing'} file organization:")
    for target_file, source_file in tqdm(planned_moves.items(), desc="Processing", unit="file"):
        try:
            tags = EasyID3(source_file)
            artist = sanitize_path_component(tags.get('artist', ['Unknown Artist'])[0], is_artist=True)
            album = sanitize_path_component(tags.get('album', ['Unknown Album'])[0], is_artist=False)
            
            # Create target directory structure
            artist_dir = target_path / artist
            album_dir = artist_dir / album
            
            if dry_run:
                tqdm.write(f"\nWould create directory structure:")
                tqdm.write(f"  {artist_dir}")
                tqdm.write(f"  {album_dir}")
                tqdm.write(f"Would move:")
                tqdm.write(f"  {source_file}")
                tqdm.write(f"To:")
                tqdm.write(f"  {target_file}")
            else:
                # Create directories if they don't exist
                album_dir.mkdir(parents=True, exist_ok=True)
                
                # Move the file
                shutil.move(str(source_file), str(target_file))
                tqdm.write(f"Moved: {source_file} -> {target_file}")
                
        except Exception as e:
            tqdm.write(f"\nError organizing {source_file}: {str(e)}")
            continue
    
    # Report potential conflicts
    if potential_conflicts:
        print("\nWarning: The following files would result in conflicts:")
        for source, target in potential_conflicts:
            print(f"  {source} -> {target}")
            
    # Print summary
    print(f"\nSummary:")
    print(f"Total files processed: {total_files}")
    print(f"Successful moves planned: {len(planned_moves)}")
    print(f"Potential conflicts: {len(potential_conflicts)}")
    print(f"Names requiring sanitization: {len(name_changes)}")

def main():
    parser = argparse.ArgumentParser(
        description='Organize MP3 files into artist/album directory structure based on ID3 tags.'
    )
    parser.add_argument(
        'source_dir',
        help='Directory containing MP3 files to organize'
    )
    parser.add_argument(
        'target_dir',
        help='Base directory for organized files'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute the file moves (default is dry run)'
    )
    
    args = parser.parse_args()
    
    organize_mp3s(args.source_dir, args.target_dir, dry_run=not args.execute)

if __name__ == "__main__":
    main()