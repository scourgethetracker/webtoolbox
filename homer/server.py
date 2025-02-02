#!/usr/bin/env python3

import http.server
import ssl
import argparse

def create_secure_server(host='0.0.0.0', port=443, cert_path='/opt/homer/server.pem'):
    """
    Creates a secure HTTPS development server for local testing.

    Parameters:
    host (str): Hostname to bind to (default: localhost for security)
    port (int): Port to listen on (default: 443)
    cert_path (str): Path to SSL certificate file
    """

    # Create the HTTP server
    httpd = http.server.HTTPServer(
        (host, port),
        http.server.SimpleHTTPRequestHandler
    )

    # Configure SSL/TLS
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print(f"Starting secure development server at https://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server")
        httpd.server_close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run a secure local development server')
    parser.add_argument('--port', type=int, default=443,
                      help='Port to run server on (default: 443)')
    parser.add_argument('--cert', type=str, default='./server.pem',
                      help='Path to SSL certificate file')

    args = parser.parse_args()
    create_secure_server(port=args.port, cert_path=args.cert)
