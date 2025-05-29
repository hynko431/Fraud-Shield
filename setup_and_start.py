#!/usr/bin/env python3
"""
FraudShield Setup and Start Script
Ensures all prerequisites are met before starting the services.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        return False
    logger.info(f"✅ Python version: {sys.version}")
    return True

def check_required_files():
    """Check if all required files exist."""
    required_files = [
        'api_gateway.py',
        'model_service.py', 
        'analytics_service.py',
        'database_service.py',
        'notification_service.py',
        'batch_processing_service.py',
        'monitoring_service.py',
        'ingest_service.py',
        'start_services.py',
        'start_frontend.py',
        'requirements.txt',
        'config.js',
        'ap.html'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"❌ Missing required files: {missing_files}")
        return False
    
    logger.info("✅ All required files present")
    return True

def install_dependencies():
    """Install Python dependencies."""
    try:
        logger.info("📦 Installing Python dependencies...")
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], capture_output=True, text=True, check=True)
        
        logger.info("✅ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install dependencies: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def create_model():
    """Create the fraud detection model if it doesn't exist."""
    model_path = Path('fraud_detection_model.pkl')
    
    if model_path.exists():
        logger.info("✅ Fraud detection model already exists")
        return True
    
    try:
        logger.info("🤖 Creating fraud detection model...")
        result = subprocess.run([
            sys.executable, 'create_model.py'
        ], capture_output=True, text=True, check=True)
        
        if model_path.exists():
            logger.info("✅ Fraud detection model created successfully")
            return True
        else:
            logger.error("❌ Model file not found after creation")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to create model: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def setup_environment():
    """Set up environment configuration."""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists() and env_example.exists():
        logger.info("📝 Creating .env file from template...")
        try:
            with open(env_example, 'r') as src, open(env_file, 'w') as dst:
                dst.write(src.read())
            logger.info("✅ .env file created (please review and update as needed)")
        except Exception as e:
            logger.warning(f"⚠️  Could not create .env file: {e}")
    
    # Create data directory
    data_dir = Path('data')
    if not data_dir.exists():
        data_dir.mkdir()
        logger.info("✅ Data directory created")
    
    # Create transaction storage directory
    storage_dir = Path('transaction_storage')
    if not storage_dir.exists():
        storage_dir.mkdir()
        logger.info("✅ Transaction storage directory created")
    
    return True

def check_ports():
    """Check if required ports are available."""
    import socket
    
    required_ports = [8000, 8001, 8002, 8003, 8004, 8005, 8006, 8080, 9001]
    busy_ports = []
    
    for port in required_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
            except OSError:
                busy_ports.append(port)
    
    if busy_ports:
        logger.warning(f"⚠️  Ports already in use: {busy_ports}")
        logger.warning("   Services may fail to start if these ports are needed")
        return False
    
    logger.info("✅ All required ports are available")
    return True

def start_services():
    """Start all backend services."""
    try:
        logger.info("🚀 Starting FraudShield services...")
        
        # Start services in background
        process = subprocess.Popen([
            sys.executable, 'start_services.py'
        ])
        
        logger.info(f"✅ Services started with PID {process.pid}")
        logger.info("   Check the service logs for detailed status")
        
        return process
        
    except Exception as e:
        logger.error(f"❌ Failed to start services: {e}")
        return None

def start_frontend():
    """Start the frontend server."""
    try:
        logger.info("🌐 Starting frontend server...")
        
        # Start frontend in background
        process = subprocess.Popen([
            sys.executable, 'start_frontend.py'
        ])
        
        logger.info(f"✅ Frontend started with PID {process.pid}")
        return process
        
    except Exception as e:
        logger.error(f"❌ Failed to start frontend: {e}")
        return None

def main():
    """Main setup and start function."""
    logger.info("🔧 FraudShield Setup and Start")
    logger.info("=" * 50)
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    if not check_required_files():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        logger.error("Failed to install dependencies. Please install manually:")
        logger.error("pip install -r requirements.txt")
        sys.exit(1)
    
    # Set up environment
    if not setup_environment():
        logger.error("Failed to set up environment")
        sys.exit(1)
    
    # Create model
    if not create_model():
        logger.error("Failed to create fraud detection model")
        sys.exit(1)
    
    # Check ports
    check_ports()  # Warning only, don't exit
    
    # Start services
    services_process = start_services()
    if not services_process:
        logger.error("Failed to start services")
        sys.exit(1)
    
    # Wait a moment for services to start
    import time
    time.sleep(5)
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        logger.error("Failed to start frontend")
        # Don't exit, services are still running
    
    logger.info("\n" + "=" * 50)
    logger.info("🎉 FraudShield Setup Complete!")
    logger.info("\n📋 Access Points:")
    logger.info("   • Web Application: http://localhost:8080/ap.html")
    logger.info("   • API Gateway: http://localhost:8000")
    logger.info("   • Service Status: http://localhost:8000/services/status")
    logger.info("\n🔧 Management:")
    logger.info("   • Test Services: python test_services.py")
    logger.info("   • Stop Services: Ctrl+C or kill the processes")
    logger.info("\n📚 Documentation:")
    logger.info("   • Backend README: BACKEND_README.md")
    logger.info("   • Frontend README: FRONTEND_README.md")
    
    try:
        # Keep script running
        logger.info("\n⏳ Services are running. Press Ctrl+C to stop...")
        services_process.wait()
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping services...")
        services_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        logger.info("✅ Services stopped")

if __name__ == '__main__':
    main()
