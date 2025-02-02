#!/usr/bin/env python3

import requests
import sys
import os
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin
from abc import ABC, abstractmethod

class ConfigError(Exception):
    """Raised when there's an error with the configuration."""
    pass

def load_config() -> Dict:
    """Load configuration from ~/.config/arr-unmonitor/config.yaml.
    
    Returns:
        Dictionary containing configuration values
        
    Raises:
        ConfigError: If config file is missing or invalid
    """
    config_dir = Path.home() / '.config' / 'arr-unmonitor'
    config_file = config_dir / 'config.yaml'
    
    if not config_file.exists():
        # Create default config file
        config_dir.mkdir(parents=True, exist_ok=True)
        default_config = {
            'radarr': {
                'enabled': True,
                'host': 'http://localhost:7878',
                'api_key': 'your-radarr-api-key-here'
            },
            'sonarr': {
                'enabled': True,
                'host': 'http://localhost:8989',
                'api_key': 'your-sonarr-api-key-here'
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.safe_dump(default_config, f)
            
        raise ConfigError(
            f"Created default configuration file at {config_file}. "
            "Please edit it with your Radarr and Sonarr settings."
        )
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            
        if not isinstance(config, dict):
            raise ConfigError("Configuration file must contain a YAML dictionary")
            
        required_sections = ['radarr', 'sonarr']
        required_keys = ['host', 'api_key', 'enabled']
        
        for section in required_sections:
            if section not in config:
                raise ConfigError(f"Configuration file is missing '{section}' section")
                
            if not isinstance(config[section], dict):
                raise ConfigError(f"'{section}' section must be a dictionary")
                
            missing_keys = [key for key in required_keys if key not in config[section]]
            if missing_keys:
                raise ConfigError(
                    f"'{section}' section is missing required keys: {', '.join(missing_keys)}"
                )
            
        return config
        
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing configuration file: {str(e)}")

class ArrAPI(ABC):
    """Base class for *arr APIs."""
    
    def __init__(self, host: str, api_key: str):
        """Initialize API with host URL and API key.
        
        Args:
            host: Base URL of service instance
            api_key: API key
        """
        self.host = host.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': self.api_key,
            'Accept': 'application/json'
        })

    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> requests.Response:
        """Make HTTP request to API.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Request payload
            
        Returns:
            Response object
        """
        url = urljoin(self.host, f'/api/v3/{endpoint}')
        response = self.session.request(method, url, json=data)
        response.raise_for_status()
        return response
    
    @abstractmethod
    def get_all_items(self) -> List[Dict]:
        """Get all monitored items."""
        pass
        
    @abstractmethod
    def update_item(self, item: Dict) -> Dict:
        """Update an item."""
        pass
        
    @abstractmethod
    def get_item_display_name(self, item: Dict) -> str:
        """Get display name for an item."""
        pass

class RadarrAPI(ArrAPI):
    """Radarr API client."""
    
    def get_all_items(self) -> List[Dict]:
        return self._make_request('movie').json()
    
    def update_item(self, item: Dict) -> Dict:
        return self._make_request('movie', method='PUT', data=item).json()
    
    def get_item_display_name(self, item: Dict) -> str:
        return f"{item['title']} ({item['year']})"

class SonarrAPI(ArrAPI):
    """Sonarr API client."""
    
    def get_all_items(self) -> List[Dict]:
        return self._make_request('series').json()
    
    def update_item(self, item: Dict) -> Dict:
        return self._make_request('series', method='PUT', data=item).json()
    
    def get_item_display_name(self, item: Dict) -> str:
        return f"{item['title']}"

def unmonitor_downloaded_items(api: ArrAPI, service_name: str) -> tuple[int, int]:
    """Unmonitor all downloaded items.
    
    Args:
        api: API instance
        service_name: Name of service for logging
        
    Returns:
        Tuple of (total items processed, number of items unmonitored)
    """
    print(f"\nProcessing {service_name}...")
    items = api.get_all_items()
    unmonitored_count = 0
    
    for item in items:
        if item.get('hasFile', False) and item.get('monitored', False):
            item['monitored'] = False
            try:
                api.update_item(item)
                unmonitored_count += 1
                print(f"Unmonitored: {api.get_item_display_name(item)}")
            except requests.exceptions.RequestException as e:
                print(f"Error updating {api.get_item_display_name(item)}: {str(e)}", 
                      file=sys.stderr)
    
    return len(items), unmonitored_count

def main():
    try:
        config = load_config()
        results = []
        
        # Process Radarr if enabled
        if config['radarr']['enabled']:
            try:
                api = RadarrAPI(config['radarr']['host'], config['radarr']['api_key'])
                results.append(('Radarr', *unmonitor_downloaded_items(api, 'Radarr')))
            except requests.exceptions.RequestException as e:
                print(f"Error connecting to Radarr: {str(e)}", file=sys.stderr)
        
        # Process Sonarr if enabled
        if config['sonarr']['enabled']:
            try:
                api = SonarrAPI(config['sonarr']['host'], config['sonarr']['api_key'])
                results.append(('Sonarr', *unmonitor_downloaded_items(api, 'Sonarr')))
            except requests.exceptions.RequestException as e:
                print(f"Error connecting to Sonarr: {str(e)}", file=sys.stderr)
        
        # Print summary
        if results:
            print("\nSummary:")
            for service, total, unmonitored in results:
                print(f"{service}:")
                print(f"  Total items processed: {total}")
                print(f"  Items unmonitored: {unmonitored}")
        else:
            print("\nNo services were processed. Please check your configuration.")
    
    except ConfigError as e:
        print(f"Configuration error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()