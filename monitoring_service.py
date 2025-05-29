#!/usr/bin/env python3
"""
FraudShield Monitoring Service
Provides system monitoring, health checks, and performance metrics.
Runs on port 8006.
"""

import os
import json
import logging
import traceback
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import psutil
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
SERVICES = {
    'api_gateway': {'url': 'http://localhost:8000', 'name': 'API Gateway'},
    'model_service': {'url': 'http://localhost:8001', 'name': 'Model Service'},
    'analytics': {'url': 'http://localhost:8002', 'name': 'Analytics Service'},
    'database': {'url': 'http://localhost:8003', 'name': 'Database Service'},
    'notification': {'url': 'http://localhost:8004', 'name': 'Notification Service'},
    'batch_processing': {'url': 'http://localhost:8005', 'name': 'Batch Processing Service'},
    'ingest_service': {'url': 'http://localhost:9001', 'name': 'Ingest Service'}
}

MONITORING_CONFIG = {
    'check_interval': 30,  # seconds
    'timeout': 10,  # seconds
    'history_retention': 1440,  # minutes (24 hours)
    'alert_thresholds': {
        'cpu_percent': 80,
        'memory_percent': 85,
        'disk_percent': 90,
        'response_time': 5.0  # seconds
    }
}

class SystemMonitor:
    """Monitors system resources and service health."""
    
    def __init__(self):
        self.service_status = {}
        self.system_metrics = []
        self.alerts = []
        self.monitoring_active = False
        self.last_check = None
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics (if available)
            try:
                network = psutil.net_io_counters()
                network_stats = {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                }
            except:
                network_stats = None
            
            # Process count
            process_count = len(psutil.pids())
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'network': network_stats,
                'processes': process_count
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def check_service_health(self, service_id: str, service_config: Dict) -> Dict[str, Any]:
        """Check health of a specific service."""
        try:
            start_time = time.time()
            
            response = requests.get(
                f"{service_config['url']}/health",
                timeout=MONITORING_CONFIG['timeout']
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    health_data = response.json()
                    status = 'healthy'
                except:
                    health_data = {'message': response.text}
                    status = 'healthy'
            else:
                health_data = {'error': f'HTTP {response.status_code}'}
                status = 'unhealthy'
            
            return {
                'service_id': service_id,
                'name': service_config['name'],
                'url': service_config['url'],
                'status': status,
                'response_time': round(response_time, 3),
                'timestamp': datetime.now().isoformat(),
                'health_data': health_data
            }
            
        except requests.exceptions.ConnectionError:
            return {
                'service_id': service_id,
                'name': service_config['name'],
                'url': service_config['url'],
                'status': 'unavailable',
                'response_time': None,
                'timestamp': datetime.now().isoformat(),
                'error': 'Connection refused'
            }
        except requests.exceptions.Timeout:
            return {
                'service_id': service_id,
                'name': service_config['name'],
                'url': service_config['url'],
                'status': 'timeout',
                'response_time': MONITORING_CONFIG['timeout'],
                'timestamp': datetime.now().isoformat(),
                'error': 'Request timeout'
            }
        except Exception as e:
            return {
                'service_id': service_id,
                'name': service_config['name'],
                'url': service_config['url'],
                'status': 'error',
                'response_time': None,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def check_all_services(self) -> Dict[str, Any]:
        """Check health of all services."""
        results = {}
        
        for service_id, service_config in SERVICES.items():
            results[service_id] = self.check_service_health(service_id, service_config)
        
        return results
    
    def check_system_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for system alerts based on thresholds."""
        alerts = []
        thresholds = MONITORING_CONFIG['alert_thresholds']
        
        # CPU alert
        if metrics.get('cpu', {}).get('percent', 0) > thresholds['cpu_percent']:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f"High CPU usage: {metrics['cpu']['percent']:.1f}%",
                'value': metrics['cpu']['percent'],
                'threshold': thresholds['cpu_percent'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Memory alert
        if metrics.get('memory', {}).get('percent', 0) > thresholds['memory_percent']:
            alerts.append({
                'type': 'memory_high',
                'severity': 'warning',
                'message': f"High memory usage: {metrics['memory']['percent']:.1f}%",
                'value': metrics['memory']['percent'],
                'threshold': thresholds['memory_percent'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Disk alert
        if metrics.get('disk', {}).get('percent', 0) > thresholds['disk_percent']:
            alerts.append({
                'type': 'disk_high',
                'severity': 'critical',
                'message': f"High disk usage: {metrics['disk']['percent']:.1f}%",
                'value': metrics['disk']['percent'],
                'threshold': thresholds['disk_percent'],
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    def check_service_alerts(self, service_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for service alerts."""
        alerts = []
        
        for service_id, status in service_status.items():
            # Service down alert
            if status['status'] in ['unavailable', 'unhealthy', 'error']:
                alerts.append({
                    'type': 'service_down',
                    'severity': 'critical',
                    'message': f"Service {status['name']} is {status['status']}",
                    'service_id': service_id,
                    'service_name': status['name'],
                    'timestamp': datetime.now().isoformat()
                })
            
            # Slow response alert
            elif (status.get('response_time') and 
                  status['response_time'] > MONITORING_CONFIG['alert_thresholds']['response_time']):
                alerts.append({
                    'type': 'slow_response',
                    'severity': 'warning',
                    'message': f"Service {status['name']} slow response: {status['response_time']:.2f}s",
                    'service_id': service_id,
                    'service_name': status['name'],
                    'response_time': status['response_time'],
                    'threshold': MONITORING_CONFIG['alert_thresholds']['response_time'],
                    'timestamp': datetime.now().isoformat()
                })
        
        return alerts
    
    def store_metrics(self, metrics: Dict[str, Any]):
        """Store metrics in memory (in production, use database)."""
        self.system_metrics.append(metrics)
        
        # Keep only recent metrics
        cutoff_time = datetime.now() - timedelta(minutes=MONITORING_CONFIG['history_retention'])
        self.system_metrics = [
            m for m in self.system_metrics
            if datetime.fromisoformat(m['timestamp']) > cutoff_time
        ]
    
    def store_alerts(self, alerts: List[Dict[str, Any]]):
        """Store alerts in memory."""
        self.alerts.extend(alerts)
        
        # Keep only recent alerts
        cutoff_time = datetime.now() - timedelta(minutes=MONITORING_CONFIG['history_retention'])
        self.alerts = [
            a for a in self.alerts
            if datetime.fromisoformat(a['timestamp']) > cutoff_time
        ]
    
    def monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("Starting monitoring loop")
        
        while self.monitoring_active:
            try:
                # Get system metrics
                metrics = self.get_system_metrics()
                self.store_metrics(metrics)
                
                # Check service health
                service_status = self.check_all_services()
                self.service_status = service_status
                
                # Check for alerts
                system_alerts = self.check_system_alerts(metrics)
                service_alerts = self.check_service_alerts(service_status)
                
                all_alerts = system_alerts + service_alerts
                if all_alerts:
                    self.store_alerts(all_alerts)
                    logger.warning(f"Generated {len(all_alerts)} alerts")
                
                self.last_check = datetime.now().isoformat()
                
                # Wait for next check
                time.sleep(MONITORING_CONFIG['check_interval'])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(MONITORING_CONFIG['check_interval'])
    
    def start_monitoring(self):
        """Start monitoring in background thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            thread.start()
            logger.info("Monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring_active = False
        logger.info("Monitoring stopped")
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get system overview."""
        current_metrics = self.get_system_metrics()
        
        # Count services by status
        service_counts = {'healthy': 0, 'unhealthy': 0, 'unavailable': 0, 'error': 0}
        for status in self.service_status.values():
            service_counts[status['status']] = service_counts.get(status['status'], 0) + 1
        
        # Count recent alerts by severity
        recent_alerts = [a for a in self.alerts if 
                        datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(hours=1)]
        alert_counts = {'critical': 0, 'warning': 0, 'info': 0}
        for alert in recent_alerts:
            alert_counts[alert['severity']] = alert_counts.get(alert['severity'], 0) + 1
        
        return {
            'system_status': 'healthy' if service_counts['healthy'] == len(SERVICES) else 'degraded',
            'services': {
                'total': len(SERVICES),
                'healthy': service_counts['healthy'],
                'unhealthy': service_counts['unhealthy'] + service_counts['unavailable'] + service_counts['error']
            },
            'alerts': {
                'total_recent': len(recent_alerts),
                'critical': alert_counts['critical'],
                'warning': alert_counts['warning']
            },
            'system_metrics': current_metrics,
            'last_check': self.last_check,
            'monitoring_active': self.monitoring_active
        }

# Initialize monitor
system_monitor = SystemMonitor()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Monitoring Service',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'monitoring_active': system_monitor.monitoring_active,
        'services_monitored': len(SERVICES),
        'config': MONITORING_CONFIG
    })

@app.route('/start', methods=['POST'])
def start_monitoring():
    """Start monitoring."""
    try:
        system_monitor.start_monitoring()
        return jsonify({
            'status': 'started',
            'message': 'Monitoring started successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop_monitoring():
    """Stop monitoring."""
    try:
        system_monitor.stop_monitoring()
        return jsonify({
            'status': 'stopped',
            'message': 'Monitoring stopped successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/overview', methods=['GET'])
def get_system_overview():
    """Get system overview."""
    try:
        overview = system_monitor.get_system_overview()
        return jsonify(overview)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/services', methods=['GET'])
def get_service_status():
    """Get current service status."""
    try:
        if not system_monitor.service_status:
            # If no cached status, check now
            system_monitor.service_status = system_monitor.check_all_services()
        
        return jsonify({
            'services': system_monitor.service_status,
            'timestamp': system_monitor.last_check or datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/metrics', methods=['GET'])
def get_system_metrics():
    """Get system metrics."""
    try:
        limit = int(request.args.get('limit', 100))
        
        # Get recent metrics
        recent_metrics = system_monitor.system_metrics[-limit:]
        
        return jsonify({
            'metrics': recent_metrics,
            'count': len(recent_metrics),
            'current': system_monitor.get_system_metrics()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/alerts', methods=['GET'])
def get_alerts():
    """Get system alerts."""
    try:
        severity = request.args.get('severity')
        limit = int(request.args.get('limit', 100))
        
        alerts = system_monitor.alerts
        
        # Filter by severity if provided
        if severity:
            alerts = [a for a in alerts if a.get('severity') == severity]
        
        # Apply limit
        alerts = alerts[-limit:]
        
        return jsonify({
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting FraudShield Monitoring Service...")
    logger.info(f"Monitoring {len(SERVICES)} services")
    logger.info(f"Check interval: {MONITORING_CONFIG['check_interval']} seconds")
    
    # Start monitoring automatically
    system_monitor.start_monitoring()
    
    logger.info("Monitoring Service starting on port 8006...")
    app.run(host='0.0.0.0', port=8006, debug=False)
