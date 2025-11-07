import http.server
import socketserver
from http import HTTPStatus
import os
import sys
import mimetypes
import socket

# Check if a port is specified as a command-line argument
if len(sys.argv) > 2:
    PORT = int(sys.argv[2])
else:
    PORT = 8000

# Set the PORT environment variable for VSCode tunneling
os.environ['PORT'] = str(PORT)

# Check if a directory is specified as a command-line argument
if len(sys.argv) > 1:
    os.chdir(sys.argv[1])

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def send_response_only(self, code, message=None):
        super().send_response_only(code, message)
        
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
        
    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()
    
    def guess_type(self, path):
        # Override to set correct MIME type for .whl files
        if path.endswith('.whl'):
            return 'application/zip', None
        # Use mimetypes directly for other files
        mimetype, encoding = mimetypes.guess_type(path)
        return mimetype, encoding
    
    def log_message(self, format, *args):
        # Suppress TLS/SSL handshake errors (they're just noise)
        if len(args) > 1 and 'Bad request' in str(args[1]):
            # Check if it's a TLS handshake attempt (starts with \x16\x03)
            try:
                request_line = str(args[0] if args else '')
                if request_line.startswith('\\x16\\x03') or request_line.startswith('\x16\x03'):
                    return  # Silently ignore TLS handshake attempts
            except:
                pass
        # Log legitimate HTTP requests
        super().log_message(format, *args)

class ReusableTCPServer(socketserver.TCPServer):
    """TCPServer that allows immediate port reuse."""
    allow_reuse_address = True
    
    def server_bind(self):
        """Override to set SO_REUSEADDR before binding."""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

if __name__ == '__main__':
    handler = CORSRequestHandler
    with ReusableTCPServer(("", PORT), handler) as httpd:
        print(f"Serving directory {os.getcwd()} at port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            httpd.server_close()

