from flask import Flask, render_template_string
import os
import time
from datetime import datetime

app = Flask(__name__)

STATE_DIR = os.path.expanduser("~/.torrent-watcher")
LOG_FILE = os.path.join(STATE_DIR, "watcher.log")
PROCESSED_FILES = os.path.join(STATE_DIR, "processed_files.log")
START_TIME = os.path.join(STATE_DIR, "start_time")
PROCESSED_COUNT = os.path.join(STATE_DIR, "processed_count")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Torrent Watcher Status</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { display: flex; gap: 20px; }
        .column { flex: 1; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
        .status { background: #e8f5e9; padding: 15px; border-radius: 5px; }
    </style>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    {% if status_page %}
    <h1>Torrent Watcher Status</h1>
    <div class="status">
        <p><strong>Uptime:</strong> {{ uptime }}</p>
        <p><strong>Files Processed:</strong> {{ processed_count }}</p>
        <p><strong>Status:</strong> Running</p>
    </div>
    {% else %}
    <h1>Torrent Watcher Progress</h1>
    <div class="container">
        <div class="column">
            <h2>Recent Log Messages</h2>
            <pre>{{ log_content }}</pre>
        </div>
        <div class="column">
            <h2>Recently Processed Files</h2>
            <pre>{{ processed_files }}</pre>
        </div>
    </div>
    {% endif %}
</body>
</html>
"""

def get_uptime():
    try:
        with open(START_TIME, 'r') as f:
            start_timestamp = int(f.read().strip())
        uptime_seconds = int(time.time() - start_timestamp)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"
    except Exception as e:
        return f"Error: {str(e)}"

def get_processed_count():
    try:
        with open(PROCESSED_COUNT, 'r') as f:
            return int(f.read().strip())
    except Exception as e:
        return f"Error: {str(e)}"

def get_recent_logs():
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            return ''.join(lines[-500:])
    except Exception as e:
        return f"Error reading logs: {str(e)}"

def get_recent_files():
    try:
        with open(PROCESSED_FILES, 'r') as f:
            lines = f.readlines()
            return ''.join(lines[-50:])
    except Exception as e:
        return f"Error reading processed files: {str(e)}"

@app.route('/status')
def status():
    return render_template_string(
        HTML_TEMPLATE,
        status_page=True,
        uptime=get_uptime(),
        processed_count=get_processed_count()
    )

@app.route('/progress')
def progress():
    return render_template_string(
        HTML_TEMPLATE,
        status_page=False,
        log_content=get_recent_logs(),
        processed_files=get_recent_files()
    )

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8384)