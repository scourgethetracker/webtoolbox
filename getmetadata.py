#!/usr/bin/env python3

import ffmpeg
import os
import argparse
import csv
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
def setup_logging(log_file: str = 'video_metadata.log') -> logging.Logger:
    """
    Set up logging configuration with both file and console handlers
    
    Args:
        log_file: Path to the log file
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

class VideoMetadataExtractor:
    """Class to handle video metadata extraction operations"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.supported_extensions: Set[str] = {
            '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv'
        }

    def get_video_metadata(self, file_path: str) -> Optional[Dict]:
        """
        Extract metadata from a video file using ffprobe
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Dictionary containing video metadata or None if extraction fails
        """
        try:
            probe = ffmpeg.probe(file_path)
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            audio_info = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
            
            file_size = os.path.getsize(file_path)
            duration = float(probe['format'].get('duration', 0))
            
            metadata = {
                'filename': os.path.basename(file_path),
                'file_path': str(Path(file_path).absolute()),
                'file_size_gb': f"{file_size / (1024*1024*1024):.2f}",
                'duration_seconds': f"{duration:.2f}",
                'duration_formatted': self._format_duration(duration),
                'format': probe['format']['format_name'],
                'video_codec': video_info.get('codec_name', 'N/A'),
                'width': video_info.get('width', 'N/A'),
                'height': video_info.get('height', 'N/A'),
                'aspect_ratio': self._calculate_aspect_ratio(
                    video_info.get('width', 0),
                    video_info.get('height', 0)
                ),
                'framerate': self._calculate_framerate(video_info.get('r_frame_rate', 'N/A')),
                'bitrate_mbps': f"{float(probe['format'].get('bit_rate', 0)) / 1000000:.2f}",
                'scan_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Add audio information if available
            if audio_info:
                metadata.update({
                    'audio_codec': audio_info.get('codec_name', 'N/A'),
                    'audio_channels': audio_info.get('channels', 'N/A'),
                    'audio_sample_rate': audio_info.get('sample_rate', 'N/A')
                })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return None

    def scan_directory(self, directory: str, extensions: Optional[Set[str]] = None) -> List[Dict]:
        """
        Recursively scan directory for video files using parallel processing
        
        Args:
            directory: Directory path to scan
            extensions: Set of file extensions to process
            
        Returns:
            List of metadata dictionaries for all processed files
        """
        if extensions is None:
            extensions = self.supported_extensions
            
        video_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    video_files.append(os.path.join(root, file))
        
        metadata_list = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self.get_video_metadata, file): file 
                for file in video_files
            }
            
            for future in as_completed(future_to_file):
                metadata = future.result()
                if metadata:
                    metadata_list.append(metadata)
                    logger.info(f"Processed: {metadata['filename']}")
        
        return metadata_list

    def save_to_csv(self, metadata_list: List[Dict], output_file: str) -> bool:
        """
        Save metadata to CSV file with error handling
        
        Args:
            metadata_list: List of metadata dictionaries
            output_file: Output CSV file path
            
        Returns:
            Boolean indicating success or failure
        """
        if not metadata_list:
            logger.warning("No metadata to save")
            return False
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=metadata_list[0].keys())
                writer.writeheader()
                writer.writerows(metadata_list)
            return True
            
        except Exception as e:
            logger.error(f"Error saving CSV file: {str(e)}")
            return False

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _calculate_aspect_ratio(width: int, height: int) -> str:
        """Calculate and format aspect ratio"""
        if not width or not height:
            return 'N/A'
        
        def gcd(a: int, b: int) -> int:
            while b:
                a, b = b, a % b
            return a
        
        divisor = gcd(width, height)
        return f"{width//divisor}:{height//divisor}"

    @staticmethod
    def _calculate_framerate(r_frame_rate: str) -> str:
        """Calculate framerate from frame rate fraction"""
        try:
            num, den = map(int, r_frame_rate.split('/'))
            return f"{num/den:.2f}"
        except (ValueError, ZeroDivisionError, AttributeError):
            return 'N/A'

def main():
    parser = argparse.ArgumentParser(description='Extract video metadata from files')
    parser.add_argument('--log-file', default='video_metadata.log',
                      help='Log file path (default: video_metadata.log)')
    parser.add_argument('directory', help='Directory containing video files')
    parser.add_argument('--output', default='video_metadata.csv', 
                      help='Output CSV file name')
    parser.add_argument('--extensions', nargs='+', 
                      help='Video file extensions to scan')
    parser.add_argument('--workers', type=int, default=4,
                      help='Number of worker threads (default: 4)')
    
    args = parser.parse_args()
    
    # Set up logging with specified log file
    global logger
    logger = setup_logging(args.log_file)
    logger.debug(f"Starting video metadata extraction with arguments: {vars(args)}")
    
    if not os.path.isdir(args.directory):
        logger.error(f"Error: {args.directory} is not a valid directory")
        return
    
    extractor = VideoMetadataExtractor(max_workers=args.workers)
    
    if args.extensions:
        extensions = {ext if ext.startswith('.') else f'.{ext}' for ext in args.extensions}
    else:
        extensions = None
    
    logger.info(f"Scanning directory: {args.directory}")
    metadata_list = extractor.scan_directory(args.directory, extensions)
    
    if metadata_list:
        if extractor.save_to_csv(metadata_list, args.output):
            logger.info(f"Metadata saved to: {args.output}")
            logger.info(f"Processed {len(metadata_list)} files")
        else:
            logger.error("Failed to save metadata to CSV")
    else:
        logger.warning("No video files found or processed")

if __name__ == '__main__':
    main()