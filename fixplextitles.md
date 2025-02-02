# Plex Movie Title Fixer - User Guide

This guide explains how to set up and use the Plex Movie Title Fixer script to automatically correct movie titles in your Plex library to match their official metadata.

## Prerequisites

Before running the script, you'll need:

- Python 3.6 or higher installed on your system
- Access to your Plex Media Server
- Your Plex authentication token
- The name of your Plex movie library

## Installation

1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv plex-env
   source plex-env/bin/activate  # On Windows, use: plex-env\Scripts\activate
   ```

2. Install the required dependency:
   ```bash
   pip install plexapi
   ```

3. Save the script to a file named `fixplextitles.py`

## Getting Your Plex Token

You'll need your Plex authentication token to run the script. Here's how to find it:

1. Sign in to your Plex web interface (usually at http://localhost:32400/web)
2. Play any media item
3. Click the three dots menu (⋮) for the item
4. Select "Get Info"
5. Look at your browser's address bar - you'll see a URL with "X-Plex-Token=" followed by your token
6. Copy the token (it's a long string of letters and numbers)

## Running the Script

### Basic Usage

The script can be run with these command-line arguments:

```bash
python fixplextitles.py --url YOUR_PLEX_URL --token YOUR_TOKEN --library "Movies" --dry-run
```

Required arguments:
- `--url`: The URL of your Plex server (e.g., http://localhost:32400)
- `--token`: Your Plex authentication token
- `--library`: The name of your movie library as it appears in Plex

Optional arguments:
- `--dry-run`: Run in test mode without making any changes (recommended for first run)

### Examples

1. Test run to see what would be changed:
   ```bash
   python fixplextitles.py --url http://localhost:32400 --token abc123... --library "Movies" --dry-run
   ```

2. Actually fix the titles:
   ```bash
   python fixplextitles.py --url http://localhost:32400 --token abc123... --library "Movies"
   ```

3. Remote Plex server:
   ```bash
   python fixplextitles.py --url http://192.168.1.100:32400 --token abc123... --library "Movie Collection"
   ```

## What The Script Does

When run, the script will:

1. Connect to your Plex server
2. Find all movies where the current title doesn't match the metadata
3. In dry-run mode:
   - Show you what titles would be changed
   - No actual changes are made
4. In normal mode:
   - Update each mismatched title to match its metadata
   - Lock the title to prevent future changes
   - Log all changes made

## Troubleshooting

### Common Issues

1. **Connection Error**
   - Verify your Plex server URL is correct
   - Ensure your Plex server is running
   - Check if you can access Plex web interface

2. **Authentication Error**
   - Verify your token is correct
   - Try getting a new token

3. **Library Not Found**
   - Make sure the library name matches exactly as shown in Plex
   - Check for any special characters or spaces

4. **SSL Certificate Errors**
   - The script disables certificate validation by default
   - No action needed for self-signed certificates

### Logs

The script logs all actions and errors. Watch the console output for:
- Information about found mismatches
- Successful updates
- Any errors that occur

## Safety Features

1. Dry Run Mode
   - Use `--dry-run` to preview changes
   - No modifications are made in this mode
   - Review the proposed changes before running without dry-run

2. Logging
   - All actions are logged
   - Errors are caught and reported
   - Easy to track what changes were made

3. Title Locking
   - Updated titles are locked to prevent accidental changes
   - Preserves your manual corrections

## Best Practices

1. Always run with `--dry-run` first
2. Back up your Plex database before making changes
3. Run during low-usage periods
4. Review logs after running
5. Keep your Plex server and media organized

## Support

If you encounter issues:
1. Check the error messages in the console
2. Verify your Plex server is accessible
3. Confirm your authentication token is valid
4. Make sure your Python environment is properly set up