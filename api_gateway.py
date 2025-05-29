#!/usr/bin/env python3
"""
FraudShield API Gateway Service
Central routing, authentication, and rate limiting for all API requests.
Runs on port 8000.
"""

import os
import json
import time
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from functools import wraps

import requests
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
SERVICE_URLS = {
    'model': 'http://localhost:8001',
    'ingest': 'http://localhost:9001',
    'analytics': 'http://localhost:8002',
    'database': 'http://localhost:8003',
    'notification': 'http://localhost:8004'
}

# Rate limiting storage (in production, use Redis)
rate_limit_storage = {}

# API key storage (in production, use database)
API_KEYS = {
    'frontend': 'fs_frontend_key_123',
    'admin': 'fs_admin_key_456',
    'test': 'fs_test_key_789'
}

class RateLimiter:
    """Simple rate limiter implementation."""
    
    def __init__(self, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client."""
        now = time.time()
        window_start = now - self.window_seconds
        
        if client_id not in rate_limit_storage:
            rate_limit_storage[client_id] = []
        
        # Remove old requests
        rate_limit_storage[client_id] = [
            req_time for req_time in rate_limit_storage[client_id]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(rate_limit_storage[client_id]) >= self.max_requests:
            return False
        
        # Add current request
        rate_limit_storage[client_id].append(now)
        return True

# Rate limiter instances
default_limiter = RateLimiter(max_requests=100, window_seconds=60)
strict_limiter = RateLimiter(max_requests=10, window_seconds=60)

def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({
                'error': 'Authentication required',
                'message': 'API key is required'
            }), 401
        
        # Find client by API key
        client_id = None
        for client, key in API_KEYS.items():
            if key == api_key:
                client_id = client
                break
        
        if not client_id:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 401
        
        g.client_id = client_id
        return f(*args, **kwargs)
    
    return decorated_function

def rate_limit(limiter=None):
    """Decorator to apply rate limiting."""
    if limiter is None:
        limiter = default_limiter
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_id = getattr(g, 'client_id', request.remote_addr)
            
            if not limiter.is_allowed(client_id):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {limiter.max_requests} per {limiter.window_seconds} seconds'
                }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def forward_request(service: str, endpoint: str, method: str = None, **kwargs):
    """Forward request to backend service."""
    if service not in SERVICE_URLS:
        return {'error': f'Unknown service: {service}'}, 404
    
    url = f"{SERVICE_URLS[service]}{endpoint}"
    method = method or request.method.lower()
    
    try:
        # Prepare request data
        request_kwargs = {
            'timeout': 30,
            'headers': {'Content-Type': 'application/json'}
        }
        
        if method in ['post', 'put', 'patch']:
            if request.is_json:
                request_kwargs['json'] = request.get_json()
            else:
                request_kwargs['data'] = request.get_data()
        
        # Add query parameters
        if request.args:
            request_kwargs['params'] = request.args
        
        # Override with any provided kwargs
        request_kwargs.update(kwargs)
        
        # Make request
        response = getattr(requests, method)(url, **request_kwargs)
        
        # Return response
        try:
            return response.json(), response.status_code
        except:
            return {'message': response.text}, response.status_code
            
    except requests.exceptions.ConnectionError:
        return {
            'error': 'Service unavailable',
            'message': f'{service.title()} service is not available'
        }, 503
    except requests.exceptions.Timeout:
        return {
            'error': 'Request timeout',
            'message': f'Request to {service} service timed out'
        }, 504
    except Exception as e:
        logger.error(f"Error forwarding request to {service}: {str(e)}")
        return {
            'error': 'Gateway error',
            'message': 'An error occurred while processing the request'
        }, 500

@app.route('/health', methods=['GET'])
def health_check():
    """Gateway health check."""
    return jsonify({
        'status': 'healthy',
        'service': 'API Gateway',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'services': SERVICE_URLS
    })

@app.route('/services/status', methods=['GET'])
@require_api_key
@rate_limit()
def services_status():
    """Check status of all backend services."""
    status = {}
    
    for service, url in SERVICE_URLS.items():
        try:
            response = requests.get(f"{url}/health", timeout=5)
            status[service] = {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'response_time': response.elapsed.total_seconds(),
                'url': url
            }
        except:
            status[service] = {
                'status': 'unavailable',
                'response_time': None,
                'url': url
            }
    
    return jsonify({
        'gateway_status': 'healthy',
        'services': status,
        'timestamp': datetime.utcnow().isoformat()
    })

# Model Service Routes
@app.route('/api/v1/model/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_api_key
@rate_limit()
def model_service_proxy(endpoint):
    """Proxy requests to Model Service."""
    return forward_request('model', f'/{endpoint}')

# Ingest Service Routes
@app.route('/api/v1/ingest/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_api_key
@rate_limit()
def ingest_service_proxy(endpoint):
    """Proxy requests to Ingest Service."""
    return forward_request('ingest', f'/{endpoint}')

# Analytics Service Routes
@app.route('/api/v1/analytics/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_api_key
@rate_limit()
def analytics_service_proxy(endpoint):
    """Proxy requests to Analytics Service."""
    return forward_request('analytics', f'/{endpoint}')

# Database Service Routes
@app.route('/api/v1/database/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_api_key
@rate_limit(strict_limiter)  # More restrictive for database operations
def database_service_proxy(endpoint):
    """Proxy requests to Database Service."""
    return forward_request('database', f'/{endpoint}')

# Notification Service Routes
@app.route('/api/v1/notifications/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_api_key
@rate_limit()
def notification_service_proxy(endpoint):
    """Proxy requests to Notification Service."""
    return forward_request('notification', f'/{endpoint}')

# Direct scoring endpoint for frontend compatibility
@app.route('/api/v1/score', methods=['POST'])
@require_api_key
@rate_limit()
def score_transactions():
    """Direct scoring endpoint that tries ingest service first, then model service."""
    try:
        # Try ingest service first
        result, status_code = forward_request('ingest', '/score', 'post')
        
        if status_code == 200:
            return jsonify(result), status_code
        
        # Fallback to model service
        logger.warning("Ingest service unavailable, falling back to model service")
        result, status_code = forward_request('model', '/score', 'post')
        
        if status_code == 200:
            # Add fallback indicator
            result['service_used'] = 'Model Service (fallback)'
            result['forwarded_by'] = 'API Gateway'
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in score_transactions: {str(e)}")
        return jsonify({
            'error': 'Scoring failed',
            'message': 'All scoring services are unavailable'
        }), 503

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not found',
        'message': 'The requested endpoint does not exist'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

if __name__ == '__main__':
    logger.info("Starting FraudShield API Gateway...")
    logger.info(f"Backend services: {SERVICE_URLS}")
    logger.info("API Gateway starting on port 8000...")
    app.run(host='0.0.0.0', port=8000, debug=False)
