#!/usr/bin/env python3
"""
Simple HTTP server to serve the FraudShield frontend
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

# Configuration
PORTS_TO_TRY = [3000, 5000, 8888, 9999, 8000, 8080]
DIRECTORY = Path(__file__).parent

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve files with proper MIME types"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        # Redirect root to index.html
        if self.path == '/':
            self.path = '/index.html'
        return super().do_GET()

def main():
    """Start the frontend server"""
    print("🚀 Starting FraudShield Frontend Server...")
    print(f"📁 Serving directory: {DIRECTORY}")

    # Try different ports
    for port in PORTS_TO_TRY:
        try:
            print(f"🔍 Trying port {port}...")
            with socketserver.TCPServer(("", port), CustomHTTPRequestHandler) as httpd:
                print(f"🌐 Server URL: http://localhost:{port}")
                print("📱 Frontend will open automatically in your browser")
                print("\n📋 Available pages:")
                print(f"   • Welcome page: http://localhost:{port}/")
                print(f"   • Main app: http://localhost:{port}/ap.html")
                print("\n⚠️  Make sure backend services are running:")
                print("   • Model Service: http://localhost:8001")
                print("   • Ingest Service: http://localhost:9001")
                print("\n🛑 Press Ctrl+C to stop the server")
                print("-" * 50)

                # Open browser automatically
                webbrowser.open(f'http://localhost:{port}')

                print(f"✅ Server started successfully on port {port}")
                httpd.serve_forever()

        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
            sys.exit(0)
        except OSError as e:
            if "Address already in use" in str(e) or "access" in str(e).lower():
                print(f"   Port {port} is not available, trying next...")
                continue
            else:
                print(f"❌ Error starting server on port {port}: {e}")
                continue
        except Exception as e:
            print(f"❌ Unexpected error on port {port}: {e}")
            continue

    print("❌ Could not start server on any available port")
    print("   Please check if other services are using these ports:")
    print(f"   {PORTS_TO_TRY}")
    sys.exit(1)

if __name__ == "__main__":
    main()
