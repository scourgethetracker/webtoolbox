#!/usr/bin/env python3

import argparse
import requests
import json
import os
import sys
from urllib.parse import quote
from xml.dom import minidom

class TVShowDownloader:
    def __init__(self):
        self.api_key = "2ee43bd3d3893e3fbcb31bc4ef996507"  # You'll need to get this from TVDB
        self.base_url = "https://api.thetvdb.com"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def authenticate(self):
        """Authenticate with TVDB API"""
        auth_data = {
            "apikey": self.api_key
        }
        try:
            response = requests.post(
                f"{self.base_url}/login",
                json=auth_data
            )
            response.raise_for_status()
            token = response.json()['token']
            self.headers['Authorization'] = f'Bearer {token}'
            return True
        except requests.exceptions.RequestException as e:
            print(f"Authentication failed: {e}")
            return False

    def search_show(self, show_name):
        """Search for a TV show"""
        try:
            response = requests.get(
                f"{self.base_url}/search/series?name={quote(show_name)}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()['data'][0]
        except (requests.exceptions.RequestException, IndexError) as e:
            print(f"Failed to find show: {e}")
            return None

    def get_show_details(self, show_id):
        """Get detailed information about a show"""
        try:
            response = requests.get(
                f"{self.base_url}/series/{show_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()['data']
        except requests.exceptions.RequestException as e:
            print(f"Failed to get show details: {e}")
            return None

    def download_artwork(self, url, filename):
        """Download artwork from URL"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to download artwork: {e}")
            return False

    def create_nfo(self, show_data, filename):
        """Create NFO file with show metadata"""
        doc = minidom.Document()
        tvshow = doc.createElement('tvshow')
        doc.appendChild(tvshow)

        # Add basic metadata
        elements = {
            'title': show_data.get('seriesName', ''),
            'plot': show_data.get('overview', ''),
            'rating': str(show_data.get('rating', '')),
            'year': show_data.get('firstAired', '')[:4] if show_data.get('firstAired') else '',
            'genre': show_data.get('genre', []),
            'studio': show_data.get('network', ''),
            'status': show_data.get('status', '')
        }

        for key, value in elements.items():
            if value:
                elem = doc.createElement(key)
                if isinstance(value, list):
                    for item in value:
                        sub_elem = doc.createElement(key)
                        text = doc.createTextNode(str(item))
                        sub_elem.appendChild(text)
                        tvshow.appendChild(sub_elem)
                else:
                    text = doc.createTextNode(str(value))
                    elem.appendChild(text)
                    tvshow.appendChild(elem)

        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(doc.toprettyxml(indent='  '))

def main():
    parser = argparse.ArgumentParser(description='Download TV show artwork and metadata')
    parser.add_argument('show_name', help='Name of the TV show')
    parser.add_argument('--output-dir', default='.',
                       help='Output directory for downloaded files')
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    downloader = TVShowDownloader()
    
    # Authenticate with TVDB
    if not downloader.authenticate():
        sys.exit(1)

    # Search for show
    show = downloader.search_show(args.show_name)
    if not show:
        sys.exit(1)

    # Get detailed information
    show_details = downloader.get_show_details(show['id'])
    if not show_details:
        sys.exit(1)

    # Download poster if available
    if show_details.get('poster'):
        poster_filename = os.path.join(args.output_dir, 'poster.jpg')
        downloader.download_artwork(show_details['poster'], poster_filename)

    # Download fanart if available
    if show_details.get('fanart'):
        fanart_filename = os.path.join(args.output_dir, 'fanart.jpg')
        downloader.download_artwork(show_details['fanart'], fanart_filename)

    # Create NFO file
    nfo_filename = os.path.join(args.output_dir, 'tvshow.nfo')
    downloader.create_nfo(show_details, nfo_filename)

if __name__ == "__main__":
    main()