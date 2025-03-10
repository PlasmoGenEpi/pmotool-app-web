import http.server
import socketserver
from http import HTTPStatus
import os
import sys

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

if __name__ == '__main__':
    handler = CORSRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Serving directory {os.getcwd()} at port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            httpd.server_close()

