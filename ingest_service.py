#!/usr/bin/env python3
"""
FraudShield Ingest Service
Handles transaction ingestion, storage, and forwards scoring requests to Model Service.
Runs on port 9001.
"""

import os
import json
import logging
import traceback
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration
MODEL_SERVICE_URL = 'http://localhost:8001'
STORAGE_DIR = Path('transaction_storage')
STORAGE_DIR.mkdir(exist_ok=True)

# In-memory transaction store (for demo purposes)
transaction_store = []

def store_transaction(transaction: Dict[str, Any]) -> bool:
    """
    Store transaction data to file and in-memory store.
    
    Args:
        transaction: Transaction data dictionary
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Add timestamp
        transaction['ingested_at'] = datetime.utcnow().isoformat()
        
        # Store in memory
        transaction_store.append(transaction)
        
        # Store to file (append to daily file)
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        file_path = STORAGE_DIR / f'transactions_{date_str}.jsonl'
        
        with open(file_path, 'a') as f:
            f.write(json.dumps(transaction) + '\n')
        
        logger.info(f"Transaction stored: {transaction.get('transaction_id', 'unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store transaction: {str(e)}")
        return False

def forward_to_model_service(transactions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Forward scoring request to Model Service.
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        Response from Model Service or None if failed
    """
    try:
        response = requests.post(
            f'{MODEL_SERVICE_URL}/score',
            json={'transactions': transactions},
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Model Service returned status {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to Model Service: {str(e)}")
        return None

def check_model_service_health() -> bool:
    """Check if Model Service is available."""
    try:
        response = requests.get(f'{MODEL_SERVICE_URL}/health', timeout=5)
        return response.status_code == 200
    except:
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    model_service_healthy = check_model_service_health()
    
    status = {
        'status': 'healthy' if model_service_healthy else 'degraded',
        'service': 'Ingest Service',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'model_service_available': model_service_healthy,
        'transactions_stored': len(transaction_store)
    }
    
    if not model_service_healthy:
        status['message'] = 'Model Service unavailable'
    
    return jsonify(status)

@app.route('/ingest', methods=['POST'])
def ingest_transaction():
    """
    Ingest a single transaction for storage.
    
    Expected input:
    {
        "transaction": {
            "transaction_id": "test_123",
            "step": 1,
            "type": "PAYMENT",
            "amount": 1000.0,
            "nameOrig": "C123456789",
            "oldbalanceOrg": 5000.0,
            "newbalanceOrig": 4000.0,
            "nameDest": "M987654321",
            "oldbalanceDest": 0.0,
            "newbalanceDest": 0.0
        }
    }
    
    Returns:
    {
        "status": "success",
        "transaction_id": "test_123",
        "ingested_at": "2024-01-01T12:00:00Z"
    }
    """
    try:
        data = request.get_json()
        if not data or 'transaction' not in data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request must contain "transaction" object'
            }), 400
        
        transaction = data['transaction']
        
        # Store the transaction
        if store_transaction(transaction):
            return jsonify({
                'status': 'success',
                'transaction_id': transaction.get('transaction_id', 'unknown'),
                'ingested_at': datetime.utcnow().isoformat(),
                'service': 'Ingest Service'
            })
        else:
            return jsonify({
                'error': 'Storage failed',
                'message': 'Failed to store transaction'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in ingest_transaction: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/score', methods=['POST'])
def score_transactions():
    """
    Score transactions by forwarding to Model Service and optionally storing them.
    
    Expected input:
    {
        "transactions": [...],
        "store": true  // optional, default false
    }
    
    Returns: Same format as Model Service with additional metadata
    """
    try:
        data = request.get_json()
        if not data or 'transactions' not in data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request must contain "transactions" array'
            }), 400
        
        transactions = data['transactions']
        store_flag = data.get('store', False)
        
        # Forward to Model Service
        model_response = forward_to_model_service(transactions)
        
        if model_response is None:
            return jsonify({
                'error': 'Model Service unavailable',
                'message': 'Could not connect to fraud detection model'
            }), 503
        
        # Optionally store transactions
        if store_flag:
            for transaction in transactions:
                store_transaction(transaction)
        
        # Add Ingest Service metadata
        model_response['forwarded_by'] = 'Ingest Service'
        model_response['forwarded_at'] = datetime.utcnow().isoformat()
        
        return jsonify(model_response)
        
    except Exception as e:
        logger.error(f"Error in score_transactions: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/transactions', methods=['GET'])
def get_transactions():
    """
    Get stored transactions with optional filtering.
    
    Query parameters:
    - limit: Maximum number of transactions to return (default: 100)
    - offset: Number of transactions to skip (default: 0)
    - date: Filter by date (YYYY-MM-DD format)
    """
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        date_filter = request.args.get('date')
        
        filtered_transactions = transaction_store
        
        # Apply date filter if provided
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                filtered_transactions = [
                    tx for tx in transaction_store
                    if datetime.fromisoformat(tx['ingested_at'].replace('Z', '+00:00')).date() == filter_date
                ]
            except ValueError:
                return jsonify({
                    'error': 'Invalid date format',
                    'message': 'Date must be in YYYY-MM-DD format'
                }), 400
        
        # Apply pagination
        total = len(filtered_transactions)
        paginated_transactions = filtered_transactions[offset:offset + limit]
        
        return jsonify({
            'transactions': paginated_transactions,
            'total': total,
            'limit': limit,
            'offset': offset,
            'service': 'Ingest Service'
        })
        
    except Exception as e:
        logger.error(f"Error in get_transactions: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def get_statistics():
    """Get transaction statistics."""
    try:
        total_transactions = len(transaction_store)
        
        if total_transactions == 0:
            return jsonify({
                'total_transactions': 0,
                'service': 'Ingest Service'
            })
        
        # Calculate basic statistics
        df = pd.DataFrame(transaction_store)
        
        stats = {
            'total_transactions': total_transactions,
            'transaction_types': df['type'].value_counts().to_dict() if 'type' in df.columns else {},
            'date_range': {
                'earliest': df['ingested_at'].min() if 'ingested_at' in df.columns else None,
                'latest': df['ingested_at'].max() if 'ingested_at' in df.columns else None
            },
            'service': 'Ingest Service'
        }
        
        # Add amount statistics if available
        if 'amount' in df.columns:
            stats['amount_stats'] = {
                'mean': float(df['amount'].mean()),
                'median': float(df['amount'].median()),
                'min': float(df['amount'].min()),
                'max': float(df['amount'].max()),
                'total': float(df['amount'].sum())
            }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error in get_statistics: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/export', methods=['GET'])
def export_transactions():
    """Export transactions as CSV."""
    try:
        if not transaction_store:
            return jsonify({
                'error': 'No data',
                'message': 'No transactions available for export'
            }), 404
        
        df = pd.DataFrame(transaction_store)
        
        # Generate CSV
        csv_data = df.to_csv(index=False)
        
        response = app.response_class(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=transactions_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in export_transactions: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

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
    logger.info("Starting FraudShield Ingest Service...")
    logger.info(f"Model Service URL: {MODEL_SERVICE_URL}")
    logger.info(f"Storage directory: {STORAGE_DIR}")
    
    # Check Model Service availability
    if check_model_service_health():
        logger.info("Model Service is available")
    else:
        logger.warning("Model Service is not available - some features may be limited")
    
    # Start the Flask app
    logger.info("Ingest Service starting on port 9001...")
    app.run(host='0.0.0.0', port=9001, debug=False)
