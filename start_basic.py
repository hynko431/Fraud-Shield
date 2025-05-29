#!/usr/bin/env python3
"""
FraudShield Basic Startup Script
Starts only the essential services for basic fraud detection functionality.
"""

import os
import sys
import time
import signal
import subprocess
import threading
import logging
import webbrowser
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BasicServiceManager:
    def __init__(self):
        self.processes = {}
        self.running = True
        self.frontend_server = None

        # Essential services only
        self.services_config = [
            ('Model Service', 'model_service.py', 8001),
            ('Ingest Service', 'ingest_service.py', 9001)
        ]

    def check_prerequisites(self):
        """Check if required files exist."""
        required_files = [
            'fraud_detection_model.pkl',
            'model_service.py',
            'ingest_service.py',
            'config.js',
            'ap.html'
        ]

        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)

        if missing_files:
            logger.error(f"Missing required files: {', '.join(missing_files)}")
            return False

        return True

    def is_port_in_use(self, port):
        """Check if a port is already in use."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return False
            except OSError:
                return True

    def start_service(self, name, script, port):
        """Start a service in a subprocess."""
        try:
            logger.info(f"Starting {name} on port {port}...")

            if self.is_port_in_use(port):
                logger.warning(f"Port {port} is already in use. Attempting to start anyway...")

            process = subprocess.Popen(
                [sys.executable, script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            self.processes[name] = {
                'process': process,
                'port': port,
                'script': script
            }

            # Start output monitoring threads
            threading.Thread(
                target=self.monitor_output,
                args=(name, process.stdout, 'INFO'),
                daemon=True
            ).start()

            threading.Thread(
                target=self.monitor_output,
                args=(name, process.stderr, 'ERROR'),
                daemon=True
            ).start()

            logger.info(f"{name} started with PID {process.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to start {name}: {str(e)}")
            return False

    def monitor_output(self, service_name, stream, level):
        """Monitor service output and log it."""
        try:
            for line in iter(stream.readline, ''):
                if line.strip():
                    if level == 'ERROR':
                        logger.error(f"[{service_name}] {line.strip()}")
                    else:
                        logger.info(f"[{service_name}] {line.strip()}")
        except Exception as e:
            logger.error(f"Error monitoring {service_name} output: {str(e)}")

    def check_service_health(self, name, port):
        """Check if a service is running and healthy."""
        if name not in self.processes:
            return False

        process = self.processes[name]['process']
        if process.poll() is not None:
            return False

        # Check HTTP health endpoint
        try:
            import requests
            response = requests.get(f'http://localhost:{port}/health', timeout=5)
            return response.status_code == 200
        except:
            return False

    def start_frontend_server(self):
        """Start a simple HTTP server for the frontend."""
        try:
            logger.info("Starting frontend HTTP server on port 3000...")
            self.frontend_server = subprocess.Popen(
                [sys.executable, '-m', 'http.server', '3000'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info("Frontend server started on http://localhost:3000")
            return True
        except Exception as e:
            logger.error(f"Failed to start frontend server: {str(e)}")
            return False

    def stop_service(self, name):
        """Stop a specific service."""
        if name in self.processes:
            process = self.processes[name]['process']
            logger.info(f"Stopping {name}...")

            try:
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {name}...")
                process.kill()
                process.wait()

            del self.processes[name]
            logger.info(f"{name} stopped")

    def stop_all_services(self):
        """Stop all running services."""
        logger.info("Stopping all services...")

        # Stop frontend server first
        if self.frontend_server:
            try:
                self.frontend_server.terminate()
                self.frontend_server.wait(timeout=5)
            except:
                self.frontend_server.kill()
            logger.info("Frontend server stopped")

        # Stop backend services
        for name in list(self.processes.keys()):
            self.stop_service(name)

        self.running = False

    def run(self):
        """Main run method."""
        logger.info("🚀 FraudShield Basic Services Manager Starting...")

        # Check prerequisites
        if not self.check_prerequisites():
            return False

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Start essential services
        for name, script, port in self.services_config:
            if not self.start_service(name, script, port):
                logger.error(f"Failed to start {name}. Exiting.")
                self.stop_all_services()
                return False

            # Wait a moment for the service to start
            time.sleep(3)

        # Start frontend server
        if not self.start_frontend_server():
            logger.error("Failed to start frontend server")
            self.stop_all_services()
            return False

        # Wait for services to be ready
        time.sleep(5)

        # Health check
        logger.info("🔍 Performing health checks...")
        all_healthy = True
        for name, script, port in self.services_config:
            if self.check_service_health(name, port):
                logger.info(f"✓ {name} is running and healthy")
            else:
                logger.error(f"✗ {name} is not healthy")
                all_healthy = False

        if not all_healthy:
            logger.warning("Some services are not healthy, but continuing...")

        # Display service URLs
        logger.info("🌐 FraudShield Basic Services URLs:")
        logger.info("   • 🖥️  Web Application: http://localhost:3000/ap.html")
        logger.info("   • 🤖 Model Service: http://localhost:8001")
        logger.info("   • 📥 Ingest Service: http://localhost:9001")

        # Open browser
        try:
            webbrowser.open('http://localhost:3000/ap.html')
            logger.info("🌐 Opened web browser to FraudShield application")
        except:
            logger.info("Could not open browser automatically")

        logger.info("✅ Basic services started successfully!")
        logger.info("Press Ctrl+C to stop all services")

        # Keep running
        try:
            while self.running:
                time.sleep(5)
        except KeyboardInterrupt:
            pass

        return True

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}. Shutting down...")
        self.stop_all_services()

def main():
    """Main entry point."""
    manager = BasicServiceManager()

    try:
        success = manager.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        manager.stop_all_services()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        manager.stop_all_services()
        sys.exit(1)

if __name__ == '__main__':
    main()
