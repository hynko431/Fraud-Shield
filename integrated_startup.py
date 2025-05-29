#!/usr/bin/env python3
"""
FraudShield Integrated Startup Script
Comprehensive startup script for all FraudShield services with proper integration.
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
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegratedServiceManager:
    def __init__(self):
        self.processes = {}
        self.running = True
        self.frontend_server = None

        # Service configuration with dependencies
        self.services_config = [
            # Core services (no dependencies)
            ('Model Service', 'model_service.py', 8001, []),
            ('Database Service', 'database_service.py', 8003, []),

            # Services that depend on core services
            ('Analytics Service', 'analytics_service.py', 8002, ['Database Service']),
            ('Notification Service', 'notification_service.py', 8004, []),
            ('Batch Processing Service', 'batch_processing_service.py', 8005, ['Model Service']),
            ('Monitoring Service', 'monitoring_service.py', 8006, []),
            ('Ingest Service', 'ingest_service.py', 9001, ['Model Service']),

            # API Gateway (depends on all other services)
            ('API Gateway', 'api_gateway.py', 8000, ['Model Service', 'Ingest Service', 'Analytics Service', 'Database Service', 'Notification Service'])
        ]

    def check_prerequisites(self):
        """Check if all required files exist."""
        required_files = [
            'fraud_detection_model.pkl',
            'config.js',
            'ap.html'
        ]

        # Add service files
        for name, script, port, deps in self.services_config:
            required_files.append(script)

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
                'script': script,
                'healthy': False
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
            response = requests.get(f'http://localhost:{port}/health', timeout=5)
            healthy = response.status_code == 200
            self.processes[name]['healthy'] = healthy
            return healthy
        except:
            return False

    def wait_for_dependencies(self, dependencies):
        """Wait for dependent services to be healthy."""
        if not dependencies:
            return True

        logger.info(f"Waiting for dependencies: {', '.join(dependencies)}")
        max_wait = 30  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait:
            all_ready = True
            for dep in dependencies:
                if dep not in self.processes or not self.processes[dep]['healthy']:
                    all_ready = False
                    break

            if all_ready:
                logger.info("All dependencies are ready")
                return True

            time.sleep(1)

        logger.warning(f"Timeout waiting for dependencies: {dependencies}")
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
        logger.info("🚀 FraudShield Integrated Services Manager Starting...")

        # Check prerequisites
        if not self.check_prerequisites():
            return False

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Start services in dependency order
        for name, script, port, dependencies in self.services_config:
            # Wait for dependencies
            if not self.wait_for_dependencies(dependencies):
                logger.error(f"Dependencies not ready for {name}. Continuing anyway...")

            if not self.start_service(name, script, port):
                logger.error(f"Failed to start {name}. Exiting.")
                self.stop_all_services()
                return False

            # Wait a moment for the service to start
            time.sleep(2)

            # Check health
            if self.check_service_health(name, port):
                logger.info(f"✓ {name} is healthy")
            else:
                logger.warning(f"⚠ {name} may not be fully ready")

        # Start frontend server
        if not self.start_frontend_server():
            logger.error("Failed to start frontend server")
            self.stop_all_services()
            return False

        # Wait a moment for everything to settle
        time.sleep(3)

        # Final health check
        logger.info("🔍 Performing final health checks...")
        all_healthy = True
        for name, script, port, deps in self.services_config:
            if self.check_service_health(name, port):
                logger.info(f"✓ {name} is running and healthy")
            else:
                logger.error(f"✗ {name} is not healthy")
                all_healthy = False

        if not all_healthy:
            logger.warning("Some services are not healthy, but continuing...")

        # Display service URLs
        self.display_service_info()

        # Open browser
        try:
            webbrowser.open('http://localhost:8080/ap.html')
            logger.info("🌐 Opened web browser to FraudShield application")
        except:
            logger.info("Could not open browser automatically")

        logger.info("✅ All services started successfully!")
        logger.info("Press Ctrl+C to stop all services")

        # Keep running
        try:
            while self.running:
                time.sleep(5)
                # Optionally perform periodic health checks here
        except KeyboardInterrupt:
            pass

        return True

    def display_service_info(self):
        """Display information about running services."""
        logger.info("🌐 FraudShield Services URLs:")
        logger.info("   • 🖥️  Web Application: http://localhost:8080/ap.html")
        logger.info("   • 🚪 API Gateway: http://localhost:8000")
        logger.info("   • 🤖 Model Service: http://localhost:8001")
        logger.info("   • 📊 Analytics Service: http://localhost:8002")
        logger.info("   • 🗄️  Database Service: http://localhost:8003")
        logger.info("   • 📧 Notification Service: http://localhost:8004")
        logger.info("   • ⚙️  Batch Processing: http://localhost:8005")
        logger.info("   • 📈 Monitoring Service: http://localhost:8006")
        logger.info("   • 📥 Ingest Service: http://localhost:9001")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}. Shutting down...")
        self.stop_all_services()

def main():
    """Main entry point."""
    manager = IntegratedServiceManager()

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
