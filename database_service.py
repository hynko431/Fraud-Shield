#!/usr/bin/env python3
"""
FraudShield Database Service
Handles persistent storage of transactions, predictions, and system data.
Runs on port 8003.
"""

import os
import json
import sqlite3
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

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

# Database configuration
DB_PATH = Path('fraudshield.db')

class DatabaseManager:
    """Manages SQLite database operations."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Transactions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transaction_id TEXT UNIQUE NOT NULL,
                        step INTEGER,
                        type TEXT,
                        amount REAL,
                        nameOrig TEXT,
                        oldbalanceOrg REAL,
                        newbalanceOrig REAL,
                        nameDest TEXT,
                        oldbalanceDest REAL,
                        newbalanceDest REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        source TEXT DEFAULT 'api'
                    )
                ''')
                
                # Predictions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS predictions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transaction_id TEXT NOT NULL,
                        risk_score REAL NOT NULL,
                        prediction INTEGER,
                        confidence REAL,
                        model_version TEXT,
                        service_used TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
                    )
                ''')
                
                # System logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        level TEXT NOT NULL,
                        service TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # API usage table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS api_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id TEXT NOT NULL,
                        endpoint TEXT NOT NULL,
                        method TEXT NOT NULL,
                        status_code INTEGER,
                        response_time REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Model performance table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS model_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_version TEXT NOT NULL,
                        accuracy REAL,
                        precision_score REAL,
                        recall REAL,
                        f1_score REAL,
                        auc_score REAL,
                        evaluation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions (created_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_transaction_id ON predictions (transaction_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions (created_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs (created_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage (created_at)')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = True):
        """Execute a database query."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # Enable column access by name
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch:
                    return [dict(row) for row in cursor.fetchall()]
                else:
                    conn.commit()
                    return cursor.rowcount
                    
        except Exception as e:
            logger.error(f"Database query failed: {str(e)}")
            raise
    
    def insert_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Insert a transaction into the database."""
        try:
            query = '''
                INSERT OR REPLACE INTO transactions 
                (transaction_id, step, type, amount, nameOrig, oldbalanceOrg, 
                 newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            params = (
                transaction.get('transaction_id'),
                transaction.get('step'),
                transaction.get('type'),
                transaction.get('amount'),
                transaction.get('nameOrig'),
                transaction.get('oldbalanceOrg'),
                transaction.get('newbalanceOrig'),
                transaction.get('nameDest'),
                transaction.get('oldbalanceDest'),
                transaction.get('newbalanceDest'),
                transaction.get('source', 'api')
            )
            
            self.execute_query(query, params, fetch=False)
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert transaction: {str(e)}")
            return False
    
    def insert_prediction(self, prediction: Dict[str, Any]) -> bool:
        """Insert a prediction into the database."""
        try:
            query = '''
                INSERT INTO predictions 
                (transaction_id, risk_score, prediction, confidence, model_version, service_used)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            
            params = (
                prediction.get('transaction_id'),
                prediction.get('risk_score'),
                prediction.get('prediction'),
                prediction.get('confidence'),
                prediction.get('model_version'),
                prediction.get('service_used')
            )
            
            self.execute_query(query, params, fetch=False)
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert prediction: {str(e)}")
            return False
    
    def get_transactions(self, limit: int = 100, offset: int = 0, 
                        start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get transactions with optional filtering."""
        query = 'SELECT * FROM transactions WHERE 1=1'
        params = []
        
        if start_date:
            query += ' AND created_at >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND created_at <= ?'
            params.append(end_date)
        
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        return self.execute_query(query, tuple(params))
    
    def get_predictions(self, transaction_id: str = None, limit: int = 100) -> List[Dict]:
        """Get predictions with optional filtering."""
        if transaction_id:
            query = 'SELECT * FROM predictions WHERE transaction_id = ? ORDER BY created_at DESC'
            params = (transaction_id,)
        else:
            query = 'SELECT * FROM predictions ORDER BY created_at DESC LIMIT ?'
            params = (limit,)
        
        return self.execute_query(query, params)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}
        
        # Transaction statistics
        trans_stats = self.execute_query('''
            SELECT 
                COUNT(*) as total_transactions,
                COUNT(DISTINCT type) as unique_types,
                AVG(amount) as avg_amount,
                MIN(amount) as min_amount,
                MAX(amount) as max_amount,
                MIN(created_at) as earliest_transaction,
                MAX(created_at) as latest_transaction
            FROM transactions
        ''')
        
        if trans_stats:
            stats['transactions'] = trans_stats[0]
        
        # Prediction statistics
        pred_stats = self.execute_query('''
            SELECT 
                COUNT(*) as total_predictions,
                AVG(risk_score) as avg_risk_score,
                COUNT(CASE WHEN prediction = 1 THEN 1 END) as fraud_predictions,
                COUNT(CASE WHEN prediction = 0 THEN 1 END) as legitimate_predictions
            FROM predictions
        ''')
        
        if pred_stats:
            stats['predictions'] = pred_stats[0]
        
        # Transaction types distribution
        type_dist = self.execute_query('''
            SELECT type, COUNT(*) as count 
            FROM transactions 
            GROUP BY type 
            ORDER BY count DESC
        ''')
        
        stats['transaction_types'] = type_dist
        
        return stats

# Initialize database manager
db_manager = DatabaseManager(DB_PATH)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        db_manager.execute_query('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'service': 'Database Service',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'database': str(DB_PATH),
            'database_size': os.path.getsize(DB_PATH) if DB_PATH.exists() else 0
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'service': 'Database Service',
            'error': str(e)
        }), 503

@app.route('/transactions', methods=['POST'])
def store_transaction():
    """Store a transaction in the database."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        transaction = data.get('transaction', data)
        
        if db_manager.insert_transaction(transaction):
            return jsonify({
                'status': 'success',
                'message': 'Transaction stored successfully',
                'transaction_id': transaction.get('transaction_id')
            })
        else:
            return jsonify({'error': 'Failed to store transaction'}), 500
            
    except Exception as e:
        logger.error(f"Error storing transaction: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/transactions', methods=['GET'])
def get_transactions():
    """Get transactions from the database."""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        transactions = db_manager.get_transactions(limit, offset, start_date, end_date)
        
        return jsonify({
            'transactions': transactions,
            'count': len(transactions),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error getting transactions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/predictions', methods=['POST'])
def store_prediction():
    """Store a prediction in the database."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        prediction = data.get('prediction', data)
        
        if db_manager.insert_prediction(prediction):
            return jsonify({
                'status': 'success',
                'message': 'Prediction stored successfully'
            })
        else:
            return jsonify({'error': 'Failed to store prediction'}), 500
            
    except Exception as e:
        logger.error(f"Error storing prediction: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/predictions', methods=['GET'])
def get_predictions():
    """Get predictions from the database."""
    try:
        transaction_id = request.args.get('transaction_id')
        limit = int(request.args.get('limit', 100))
        
        predictions = db_manager.get_predictions(transaction_id, limit)
        
        return jsonify({
            'predictions': predictions,
            'count': len(predictions)
        })
        
    except Exception as e:
        logger.error(f"Error getting predictions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/statistics', methods=['GET'])
def get_statistics():
    """Get database statistics."""
    try:
        stats = db_manager.get_statistics()
        return jsonify({
            'statistics': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting FraudShield Database Service...")
    logger.info(f"Database path: {DB_PATH}")
    logger.info("Database Service starting on port 8003...")
    app.run(host='0.0.0.0', port=8003, debug=False)
