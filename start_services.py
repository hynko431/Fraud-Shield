#!/usr/bin/env python3
"""
FraudShield Services Startup Script
Starts both Model Service and Ingest Service with proper error handling and monitoring.
"""

import os
import sys
import time
import signal
import subprocess
import threading
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self):
        self.processes = {}
        self.running = True

    def start_service(self, name, script, port):
        """Start a service in a subprocess."""
        try:
            logger.info(f"Starting {name} on port {port}...")

            # Check if port is already in use
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

    def is_port_in_use(self, port):
        """Check if a port is already in use."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return False
            except OSError:
                return True

    def check_service_health(self, name):
        """Check if a service is running and healthy."""
        if name not in self.processes:
            return False

        process = self.processes[name]['process']
        return process.poll() is None

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
        for name in list(self.processes.keys()):
            self.stop_service(name)
        self.running = False

    def monitor_services(self):
        """Monitor services and restart if they crash."""
        services_config = [
            ('API Gateway', 'api_gateway.py', 8000),
            ('Model Service', 'model_service.py', 8001),
            ('Analytics Service', 'analytics_service.py', 8002),
            ('Database Service', 'database_service.py', 8003),
            ('Notification Service', 'notification_service.py', 8004),
            ('Batch Processing Service', 'batch_processing_service.py', 8005),
            ('Monitoring Service', 'monitoring_service.py', 8006),
            ('Ingest Service', 'ingest_service.py', 9001)
        ]

        while self.running:
            for name, script, port in services_config:
                if not self.check_service_health(name):
                    if name in self.processes:
                        logger.warning(f"{name} has crashed. Restarting...")
                        self.stop_service(name)

                    if self.running:  # Only restart if we're still supposed to be running
                        self.start_service(name, script, port)

            time.sleep(5)  # Check every 5 seconds

    def run(self):
        """Main run method."""
        logger.info("FraudShield Services Manager Starting...")

        # Check if required files exist
        required_files = [
            'api_gateway.py', 'model_service.py', 'analytics_service.py',
            'database_service.py', 'notification_service.py',
            'batch_processing_service.py', 'monitoring_service.py',
            'ingest_service.py', 'fraud_detection_model.pkl'
        ]
        for file in required_files:
            if not Path(file).exists():
                logger.error(f"Required file not found: {file}")
                return False

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Start services
        services_config = [
            ('API Gateway', 'api_gateway.py', 8000),
            ('Model Service', 'model_service.py', 8001),
            ('Analytics Service', 'analytics_service.py', 8002),
            ('Database Service', 'database_service.py', 8003),
            ('Notification Service', 'notification_service.py', 8004),
            ('Batch Processing Service', 'batch_processing_service.py', 8005),
            ('Monitoring Service', 'monitoring_service.py', 8006),
            ('Ingest Service', 'ingest_service.py', 9001)
        ]

        for name, script, port in services_config:
            if not self.start_service(name, script, port):
                logger.error(f"Failed to start {name}. Exiting.")
                self.stop_all_services()
                return False

        # Wait a moment for services to start
        time.sleep(3)

        # Check if services are running
        all_healthy = True
        for name, _, _ in services_config:
            if self.check_service_health(name):
                logger.info(f"✓ {name} is running")
            else:
                logger.error(f"✗ {name} failed to start")
                all_healthy = False

        if not all_healthy:
            logger.error("Some services failed to start. Stopping all services.")
            self.stop_all_services()
            return False

        logger.info("All services started successfully!")
        logger.info("🌐 FraudShield Services URLs:")
        logger.info("   • Web Application: http://localhost:8080/ap.html")
        logger.info("   • API Gateway: http://localhost:8000")
        logger.info("   • Model Service: http://localhost:8001")
        logger.info("   • Analytics Service: http://localhost:8002")
        logger.info("   • Database Service: http://localhost:8003")
        logger.info("   • Notification Service: http://localhost:8004")
        logger.info("   • Batch Processing: http://localhost:8005")
        logger.info("   • Monitoring Service: http://localhost:8006")
        logger.info("   • Ingest Service: http://localhost:9001")
        logger.info("Press Ctrl+C to stop all services")

        # Start monitoring
        try:
            self.monitor_services()
        except KeyboardInterrupt:
            pass

        return True

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}. Shutting down...")
        self.stop_all_services()

def main():
    """Main entry point."""
    manager = ServiceManager()

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
