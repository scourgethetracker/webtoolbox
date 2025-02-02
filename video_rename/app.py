#!/usr/bin/env python3

from flask import Flask, render_template, send_from_directory, jsonify, request
from functools import wraps
import os
import json
from pathlib import Path
import csv
import logging
import subprocess
import ffmpeg
from urllib.parse import unquote

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define editable metadata fields
EDITABLE_METADATA_FIELDS = {
    'global': [
        'title', 'artist', 'album', 'date', 'genre', 'description', 
        'comment', 'copyright', 'language', 'synopsis', 'show', 
        'episode_id', 'season_number', 'episode_number',
        'album_artist', 'composer', 'encoder', 'publisher',
        'track', 'disc'
    ],
    'video': [
        'title', 'language', 'handler_name'
    ],
    'audio': [
        'title', 'language', 'handler_name'
    ]
}

# Create Flask app instance first
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.urandom(24)

# Authentication settings
AUTH_USERNAME = "admin"
AUTH_PASSWORD = "changeme"  # Change this to your desired password

def check_auth(username, password):
    """Check if username/password combination is valid"""
    return username == AUTH_USERNAME and password == AUTH_PASSWORD

def requires_auth(f):
    """Decorator for routes that require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return ('Unauthorized', 401, {
                'WWW-Authenticate': 'Basic realm="Login Required"'
            })
        return f(*args, **kwargs)
    return decorated

def get_metadata_template(existing_metadata=None):
    """Create a complete metadata template with existing values"""
    template = {
        'global': {field: '' for field in EDITABLE_METADATA_FIELDS['global']},
        'video': {field: '' for field in EDITABLE_METADATA_FIELDS['video']},
        'audio': {field: '' for field in EDITABLE_METADATA_FIELDS['audio']}
    }
    
    if existing_metadata:
        for section in ['global', 'video', 'audio']:
            if section in existing_metadata:
                for field, value in existing_metadata[section].items():
                    if field in template[section]:
                        template[section][field] = value
    
    return template

def update_csv_filename(old_path, new_path):
    """Update the CSV file with the new filename in place"""
    try:
        # Read all data from CSV
        rows = []
        with open('video_metadata.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row['file_path'] == old_path:
                    # Update only the filename
                    row['filename'] = os.path.basename(new_path)
                rows.append(row)

        # Write back to the same file
        with open('video_metadata.csv', 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        app.logger.error(f"Error updating CSV: {e}")
        raise

@app.route('/')
@requires_auth
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/files')
@requires_auth
def get_files():
    """Get the contents of the video metadata CSV file"""
    try:
        with open('video_metadata.csv', 'r', encoding='utf-8') as f:
            return jsonify({'success': True, 'data': f.read()})
    except Exception as e:
        app.logger.error(f"Error reading CSV: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/metadata/<path:filepath>', methods=['GET'])
@requires_auth
def get_metadata(filepath):
    """Get full metadata for a specific file"""
    try:
        # Decode the URL-encoded path and ensure it starts with /
        decoded_path = unquote(filepath)
        if not decoded_path.startswith('/'):
            decoded_path = '/' + decoded_path
            
        path = Path(decoded_path).resolve()
        app.logger.info(f"Attempting to read metadata from: {path}")
        
        if not path.exists():
            app.logger.error(f"File not found at path: {path}")
            return jsonify({
                'success': False,
                'error': f'File not found: {decoded_path}'
            })

        probe = ffmpeg.probe(str(path))
        app.logger.info(f"Successfully probed file: {path}")
        
        # Extract existing metadata
        global_meta = probe.get('format', {}).get('tags', {})
        video_meta = next((s.get('tags', {}) for s in probe['streams'] 
                          if s['codec_type'] == 'video'), {})
        audio_meta = next((s.get('tags', {}) for s in probe['streams'] 
                          if s['codec_type'] == 'audio'), {})

        existing_metadata = {
            'global': global_meta,
            'video': video_meta,
            'audio': audio_meta
        }

        # Get complete metadata template with existing values
        template = get_metadata_template(existing_metadata)

        # Add technical metadata (non-editable, for display only)
        template['technical'] = {
            'format': probe['format'].get('format_name', ''),
            'duration': probe['format'].get('duration', ''),
            'size': probe['format'].get('size', ''),
            'bit_rate': probe['format'].get('bit_rate', ''),
            'video_codec': next((s.get('codec_name', '') for s in probe['streams'] 
                               if s['codec_type'] == 'video'), ''),
            'audio_codec': next((s.get('codec_name', '') for s in probe['streams'] 
                               if s['codec_type'] == 'audio'), ''),
            'width': next((s.get('width', '') for s in probe['streams'] 
                         if s['codec_type'] == 'video'), ''),
            'height': next((s.get('height', '') for s in probe['streams'] 
                          if s['codec_type'] == 'video'), ''),
            'frame_rate': next((s.get('r_frame_rate', '') for s in probe['streams'] 
                              if s['codec_type'] == 'video'), ''),
            'sample_rate': next((s.get('sample_rate', '') for s in probe['streams'] 
                               if s['codec_type'] == 'audio'), ''),
            'channels': next((s.get('channels', '') for s in probe['streams'] 
                            if s['codec_type'] == 'audio'), '')
        }

        return jsonify({
            'success': True,
            'metadata': template,
            'editable_fields': EDITABLE_METADATA_FIELDS
        })
    except Exception as e:
        app.logger.error(f"Error getting metadata for {decoded_path}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/metadata/<path:filepath>', methods=['POST'])
@requires_auth
def update_metadata(filepath):
    """Update metadata for a specific file"""
    try:
        # Decode the URL-encoded path and ensure it starts with /
        decoded_path = unquote(filepath)
        if not decoded_path.startswith('/'):
            decoded_path = '/' + decoded_path
            
        path = Path(decoded_path).resolve()
        app.logger.info(f"Attempting to update metadata for: {path}")
        
        if not path.exists():
            return jsonify({
                'success': False,
                'error': f'File not found: {decoded_path}'
            })

        metadata = request.json.get('metadata', {})
        
        # Create temporary file path, handling spaces correctly
        temp_path = path.with_name(f"{path.stem}_temp{path.suffix}")
        
        try:
            # Build ffmpeg command manually to ensure proper metadata handling
            command = ['ffmpeg', '-i', str(path)]
            
            # Add metadata arguments
            for section, fields in metadata.items():
                if section in ['global', 'video', 'audio']:
                    for key, value in fields.items():
                        if key in EDITABLE_METADATA_FIELDS[section] and value:
                            if section == 'global':
                                command.extend(['-metadata', f'{key}={value}'])
                            else:
                                stream_type = 'v:0' if section == 'video' else 'a:0'
                                command.extend([f'-metadata:s:{stream_type}', f'{key}={value}'])

            # Add output options
            command.extend([
                '-codec', 'copy',  # Copy all streams without re-encoding
                '-map', '0',       # Copy all streams
                str(temp_path)     # Output file
            ])

            app.logger.info(f"Running ffmpeg command: {' '.join(command)}")
            
            # Run ffmpeg command and capture output
            result = subprocess.run(
                command,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                app.logger.error(f"FFmpeg stderr: {result.stderr}")
                return jsonify({
                    'success': False,
                    'error': f'FFmpeg error: {result.stderr}'
                })

            # Replace original file with updated one
            temp_path.replace(path)
            app.logger.info(f"Successfully updated metadata for: {path}")
            
            return jsonify({
                'success': True,
                'message': 'Metadata updated successfully'
            })
        finally:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
                
    except Exception as e:
        app.logger.error(f"Error updating metadata for {decoded_path}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/refresh-metadata', methods=['POST'])
@requires_auth
def refresh_metadata():
    """Run the metadata collection script"""
    try:
        script_path = Path('~/getmetadata.py').expanduser()
        media_path = Path('/data/media/Shows')
        output_path = Path('/opt/viddeo_rename/video_metadata.csv')
        
        if not script_path.exists():
            return jsonify({
                'success': False,
                'error': f'Script not found at {script_path}'
            })

        app.logger.info(f"Running metadata script: {script_path} {media_path}")
        
        # Run the script and capture output
        result = subprocess.run(
            ['/usr/bin/env', 'python3', str(script_path), str(media_path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            app.logger.info("Metadata refresh completed successfully")
            return jsonify({
                'success': True,
                'message': 'Metadata refresh complete',
                'output': result.stdout
            })
        else:
            app.logger.error(f"Metadata refresh failed: {result.stderr}")
            return jsonify({
                'success': False,
                'error': f'Script failed with error: {result.stderr}'
            })
            
    except Exception as e:
        app.logger.error(f"Error running metadata script: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/rename', methods=['POST'])
@requires_auth
def rename_files():
    """Handle file rename requests"""
    try:
        if not request.is_json:
            return jsonify({
                'success': False, 
                'error': 'Request must be JSON',
                'results': []
            }), 400

        files = request.json.get('files', [])
        if not files:
            return jsonify({
                'success': False,
                'error': 'No files provided',
                'results': []
            })

        app.logger.info(f"Received rename request for {len(files)} files")
        results = []
        
        for file in files:
            if 'file_path' not in file or 'newName' not in file:
                app.logger.error(f"Invalid file data: {file}")
                continue

            # Decode paths in case they were encoded
            old_path = Path(unquote(file['file_path']))
            if not str(old_path).startswith('/'):
                old_path = Path('/' + str(old_path))
            
            new_name = unquote(file['newName'])
            new_path = old_path.parent / new_name
            
            app.logger.info(f"Attempting to rename {old_path} to {new_path}")
            
            try:
                old_path = old_path.resolve()
                new_path = new_path.resolve()
                
                # Ensure new path is in same directory as old path
                if old_path.parent != new_path.parent:
                    raise ValueError("Cannot move files between directories")
                
                # Check if paths are absolute
                if not old_path.is_absolute() or not new_path.is_absolute():
                    raise ValueError("Paths must be absolute")

                if old_path.exists():
                    if new_path.exists():
                        results.append({
                            'success': False,
                            'oldPath': str(old_path),
                            'error': 'Destination file already exists'
                        })
                        continue

                    # Use ffmpeg to move the file, preserving all streams and metadata
                    command = [
                        'ffmpeg',
                        '-i', str(old_path),
                        '-c', 'copy',  # Copy all streams without re-encoding
                        '-map', '0',   # Copy all streams
                        '-y',          # Overwrite output file if it exists
                        str(new_path)
                    ]

                    app.logger.info(f"Running ffmpeg command: {' '.join(command)}")
                    
                    # Run ffmpeg command and capture output
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True
                    )

                    if result.returncode != 0:
                        app.logger.error(f"FFmpeg stderr: {result.stderr}")
                        results.append({
                            'success': False,
                            'oldPath': str(old_path),
                            'error': f'FFmpeg error: {result.stderr}'
                        })
                        continue

                    # Remove the original file after successful copy
                    old_path.unlink()
                    
                    # Update the CSV file with new filename
                    update_csv_filename(str(old_path), str(new_path))
                    
                    results.append({
                        'success': True,
                        'oldPath': str(old_path),
                        'newPath': str(new_path)
                    })
                    app.logger.info(f"Successfully renamed {old_path} to {new_path}")
                else:
                    app.logger.error(f"File not found: {old_path}")
                    results.append({
                        'success': False,
                        'oldPath': str(old_path),
                        'error': 'File not found'
                    })
            except Exception as e:
                app.logger.error(f"Error renaming {old_path}: {e}")
                results.append({
                    'success': False,
                    'oldPath': str(old_path),
                    'error': str(e)
                })

        return jsonify({
            'success': any(r['success'] for r in results),
            'results': results
        })

    except Exception as e:
        app.logger.error(f"Unexpected error in rename_files: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'results': []
        })

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'success': False, 'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

def create_app():
    """Create and configure the app"""
    # Ensure required directories exist
    Path('static').mkdir(exist_ok=True)
    Path('templates').mkdir(exist_ok=True)
    return app

if __name__ == '__main__':
    create_app()
    
    # Check if SSL certificates exist
    cert_path = Path('cert.pem')
    key_path = Path('key.pem')
    
    if cert_path.exists() and key_path.exists():
        # Run with HTTPS
        app.run(
            host='0.0.0.0',
            port=5000,
            ssl_context=(str(cert_path), str(key_path)),
            debug=False
        )
    else:
        # Run without HTTPS
        print("Warning: Running without HTTPS. For secure deployment, generate SSL certificates.")
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False
        )       