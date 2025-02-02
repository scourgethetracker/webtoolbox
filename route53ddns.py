#!/usr/bin/env python3

import boto3
import netifaces
import time
import logging
from botocore.exceptions import ClientError

class Route53DDNS:
    def __init__(self, hosted_zone_id, record_name, ttl=300):
        """
        Initialize the DDNS client
        
        Args:
            hosted_zone_id (str): The Route53 hosted zone ID
            record_name (str): The fully qualified domain name to update
            ttl (int): TTL for the DNS record in seconds
        """
        self.hosted_zone_id = hosted_zone_id
        self.record_name = record_name
        self.interface_name = 'wlx2023510da7cc'
        self.ttl = ttl
        self.route53 = boto3.client('route53')
        self.logger = self._setup_logging()
        self.current_ip = None
        
    def _setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
        
    def get_interface_ip(self):
        """Get the current IP address of wlx2023510da7cc interface"""
        try:
            addresses = netifaces.ifaddresses(self.interface_name)
            if netifaces.AF_INET in addresses:
                return addresses[netifaces.AF_INET][0]['addr']
            self.logger.error(f"No IPv4 address found for interface {self.interface_name}")
            return None
        except ValueError as e:
            self.logger.error(f"Error getting interface IP: {e}")
            return None
            
    def update_route53(self, ip_address):
        """Update the Route53 A record with the new IP address"""
        try:
            response = self.route53.change_resource_record_sets(
                HostedZoneId=self.hosted_zone_id,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': 'UPSERT',
                            'ResourceRecordSet': {
                                'Name': self.record_name,
                                'Type': 'A',
                                'TTL': self.ttl,
                                'ResourceRecords': [
                                    {'Value': ip_address}
                                ]
                            }
                        }
                    ]
                }
            )
            self.logger.info(f"Successfully updated Route53 record: {self.record_name} -> {ip_address}")
            return response
        except ClientError as e:
            self.logger.error(f"Error updating Route53: {e}")
            return None
            
    def run(self, check_interval=300):
        """
        Run the DDNS client
        
        Args:
            check_interval (int): How often to check for IP changes (in seconds)
        """
        self.logger.info(f"Starting DDNS client for {self.record_name} monitoring interface {self.interface_name}")
        
        while True:
            try:
                # Get current IP
                new_ip = self.get_interface_ip()
                
                if not new_ip:
                    self.logger.error(f"Failed to get IP address from interface {self.interface_name}")
                    time.sleep(check_interval)
                    continue
                    
                # Update DNS if IP has changed
                if new_ip != self.current_ip:
                    self.logger.info(f"IP change detected: {self.current_ip} -> {new_ip}")
                    if self.update_route53(new_ip):
                        self.current_ip = new_ip
                        
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                time.sleep(check_interval)

def main():
    # Configuration
    HOSTED_ZONE_ID = 'YOUR_HOSTED_ZONE_ID'
    RECORD_NAME = 'your.domain.com'
    
    # Create and run the DDNS client
    ddns = Route53DDNS(
        hosted_zone_id=Z079735517VW4TZ29ALPG,
        record_name=u3.webtool.click
    )
    
    # Run with default 5-minute check interval
    ddns.run()

if __name__ == '__main__':
    main()