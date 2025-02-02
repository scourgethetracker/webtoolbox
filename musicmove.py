#!/usr/bin/env python3

import os
import shutil
from mutagen import File
from mutagen.easyid3 import EasyID3
from pathlib import Path

def organize_music(source_dir):
    """
    Organizes music files by artist and album based on ID3 tags.
    Also moves corresponding .lrc files to the same location.
    
    Args:
        source_dir (str): Directory containing the music files
    """
    # Convert source_dir to Path object
    source_path = Path(source_dir)
    
    # Get all MP3 files in the directory
    mp3_files = list(source_path.glob('**/*.mp3'))
    
    for mp3_file in mp3_files:
        try:
            # Load ID3 tags
            audio = EasyID3(mp3_file)
            
            # Get artist and album, use 'Unknown' if not available
            artist = audio.get('artist', ['Unknown Artist'])[0]
            album = audio.get('album', ['Unknown Album'])[0]
            
            # Remove any characters that might cause issues in file paths
            artist = "".join(c for c in artist if c.isalnum() or c in (' ', '-', '_'))
            album = "".join(c for c in album if c.isalnum() or c in (' ', '-', '_'))
            
            # Create artist and album directories
            artist_path = source_path / artist
            album_path = artist_path / album
            
            # Create directories if they don't exist
            album_path.mkdir(parents=True, exist_ok=True)
            
            # Move MP3 file
            new_mp3_path = album_path / mp3_file.name
            shutil.move(str(mp3_file), str(new_mp3_path))
            
            # Check for corresponding .lrc file
            lrc_file = mp3_file.with_suffix('.lrc')
            if lrc_file.exists():
                new_lrc_path = album_path / lrc_file.name
                shutil.move(str(lrc_file), str(new_lrc_path))
                
            print(f"Processed: {mp3_file.name} -> {artist}/{album}/")
            
        except Exception as e:
            print(f"Error processing {mp3_file.name}: {str(e)}")

def main():
    # Get the current working directory
    current_dir = os.getcwd()
    
    print("Starting music library organization...")
    print(f"Processing files in: {current_dir}")
    
    try:
        organize_music(current_dir)
        print("\nOrganization complete!")
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")

if __name__ == "__main__":
    main()