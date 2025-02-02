#!/usr/bin/env python3

import os
import argparse
import re
from pathlib import Path

def get_new_filename(filename):
    """
    Transform filename by:
    1. Checking if already in correct format first
    2. Ignoring subtitle files
    3. Removing leading two digits and the following separator
    4. Replacing underscores with spaces
    5. Enclosing four-digit years (1900-2999) in parentheses
    6. Removing any content between the year and file extension
    7. Handling malformed parentheses
    """
    # List of common subtitle extensions to ignore
    SUBTITLE_EXTENSIONS = {
        '.srt', '.sub', '.smi', '.ssa', '.ass', '.vtt', '.idx', 
        '.scc', '.ttml', '.dfxp', '.sbv', '.sup'
    }
    
    # Check if file is a subtitle
    _, ext = os.path.splitext(filename)
    if ext.lower() in SUBTITLE_EXTENSIONS:
        return filename
    # Check if file is already properly formatted
    pattern = r"^[^0-9]*[A-Za-z].*?\s\(\d{4}\)\.[^.]+$"
    if re.match(pattern, filename):
        return filename
        
    # Split into name and extension
    name, ext = os.path.splitext(filename)
    
    # Remove leading digits and separator if present
    if len(name) > 3 and name[:2].isdigit() and name[2] in ['.', ' ', '_']:
        name = name[3:]
    
    # Replace underscores with spaces
    name = name.replace('_', ' ')
    
    # Handle malformed parentheses
    open_count = name.count('(')
    close_count = name.count(')')
    if open_count != close_count:
        name = name.replace('(', '').replace(')', '')
    else:
        name = re.sub(r'\([^)]*\)', '', name).strip()
    
    # Look for a year
    year_match = re.search(r'\b(\d{4})\b', name)
    if year_match and 1900 <= int(year_match.group(1)) <= 2999:
        # Extract the year
        year = year_match.group(1)
        # Get everything before the year
        base_name = name[:year_match.start()].strip()
        # Remove trailing separators and spaces
        base_name = re.sub(r'[._\s]+$', '', base_name)
        # Create new name
        name = f"{base_name} ({year})"
    
    # Clean up any double spaces
    name = ' '.join(name.split())
    
    return name + ext

def process_directory(directory_path, execute=False):
    """
    Process all files in the given directory and its subdirectories.
    
    Args:
        directory_path (str): Path to the parent directory
        execute (bool): If True, perform the actual renaming; if False, just print what would happen
    """
    try:
        root_path = Path(directory_path)
        
        if not root_path.exists():
            print(f"Error: Directory '{directory_path}' does not exist")
            return
        
        for dirpath, _, filenames in os.walk(root_path):
            current_dir = Path(dirpath)
            
            for filename in filenames:
                old_filepath = current_dir / filename
                new_filename = get_new_filename(filename)
                new_filepath = current_dir / new_filename
                
                # Skip if no change is needed
                if filename == new_filename:
                    continue
                
                if execute:
                    try:
                        if new_filepath.exists():
                            print(f"Warning: Cannot rename '{old_filepath}' to '{new_filepath}' - target file already exists")
                            continue
                        
                        old_filepath.rename(new_filepath)
                        print(f"Renamed: '{old_filepath}' -> '{new_filepath}'")
                    except OSError as e:
                        print(f"Error renaming '{old_filepath}': {e}")
                else:
                    print(f"Would rename: '{old_filepath}' -> '{new_filepath}'")
                    
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    parser = argparse.ArgumentParser(description='Rename files by removing leading two digits and first period.')
    parser.add_argument('directory', help='Directory containing files to rename')
    parser.add_argument('--execute', action='store_true', 
                        help='Execute the renaming (default is dry run)')
    
    args = parser.parse_args()
    
    if args.execute:
        print("Running in execute mode - files will be renamed")
    else:
        print("Running in dry run mode - no files will be renamed")
    
    process_directory(args.directory, args.execute)

if __name__ == "__main__":
    main()