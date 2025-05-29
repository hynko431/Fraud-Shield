#!/usr/bin/env python3
"""
FraudShield Model Service
Provides fraud detection scoring using the trained machine learning model.
Runs on port 8001.
"""

import os
import sys
import json
import pickle
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Global variables for model and preprocessing
model = None
feature_columns = None

def load_model():
    """Load the trained fraud detection model."""
    global model, feature_columns
    
    try:
        model_path = 'fraud_detection_model.pkl'
        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            return False
            
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
            
        if isinstance(model_data, dict):
            model = model_data.get('model')
            feature_columns = model_data.get('feature_columns')
        else:
            model = model_data
            # Default feature columns based on the dataset structure
            feature_columns = [
                'step', 'amount', 'oldbalanceOrg', 'newbalanceOrig',
                'oldbalanceDest', 'newbalanceDest', 'type_CASH_OUT',
                'type_DEBIT', 'type_PAYMENT', 'type_TRANSFER', 'merchantFlag'
            ]
            
        logger.info("Model loaded successfully")
        logger.info(f"Feature columns: {feature_columns}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def preprocess_transaction(transaction: Dict[str, Any]) -> pd.DataFrame:
    """
    Preprocess a single transaction for model prediction.
    
    Args:
        transaction: Dictionary containing transaction data
        
    Returns:
        DataFrame with preprocessed features
    """
    try:
        # Create base dataframe
        df = pd.DataFrame([transaction])
        
        # Create transaction type dummy variables
        transaction_types = ['CASH_OUT', 'DEBIT', 'PAYMENT', 'TRANSFER']
        for t_type in transaction_types:
            df[f'type_{t_type}'] = (df['type'] == t_type).astype(int)
        
        # Create merchant flag (destination starts with 'M')
        df['merchantFlag'] = df['nameDest'].str.startswith('M').astype(int)
        
        # Select only the features needed by the model
        if feature_columns:
            # Ensure all required columns exist
            for col in feature_columns:
                if col not in df.columns:
                    df[col] = 0
            df = df[feature_columns]
        else:
            # Use default feature selection
            feature_cols = [
                'step', 'amount', 'oldbalanceOrg', 'newbalanceOrig',
                'oldbalanceDest', 'newbalanceDest', 'type_CASH_OUT',
                'type_DEBIT', 'type_PAYMENT', 'type_TRANSFER', 'merchantFlag'
            ]
            df = df[feature_cols]
        
        return df
        
    except Exception as e:
        logger.error(f"Error preprocessing transaction: {str(e)}")
        raise

def validate_transaction(transaction: Dict[str, Any]) -> bool:
    """
    Validate transaction data structure and types.
    
    Args:
        transaction: Dictionary containing transaction data
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        'step', 'type', 'amount', 'nameOrig', 'oldbalanceOrg',
        'newbalanceOrig', 'nameDest', 'oldbalanceDest', 'newbalanceDest'
    ]
    
    # Check required fields
    for field in required_fields:
        if field not in transaction:
            logger.warning(f"Missing required field: {field}")
            return False
    
    # Validate data types
    try:
        float(transaction['amount'])
        float(transaction['oldbalanceOrg'])
        float(transaction['newbalanceOrig'])
        float(transaction['oldbalanceDest'])
        float(transaction['newbalanceDest'])
        int(transaction['step'])
    except (ValueError, TypeError):
        logger.warning("Invalid numeric values in transaction")
        return False
    
    # Validate transaction type
    valid_types = ['PAYMENT', 'TRANSFER', 'CASH_OUT', 'DEBIT']
    if transaction['type'] not in valid_types:
        logger.warning(f"Invalid transaction type: {transaction['type']}")
        return False
    
    return True

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    status = {
        'status': 'healthy',
        'service': 'Model Service',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'model_loaded': model is not None
    }
    
    if model is None:
        status['status'] = 'degraded'
        status['message'] = 'Model not loaded'
        return jsonify(status), 503
    
    return jsonify(status)

@app.route('/score', methods=['POST'])
def score_transactions():
    """
    Score transactions for fraud risk.
    
    Expected input:
    {
        "transactions": [
            {
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
        ]
    }
    
    Returns:
    {
        "results": [
            {
                "transaction_id": "test_123",
                "risk": 0.15,
                "prediction": 0,
                "confidence": 0.85
            }
        ],
        "processed_at": "2024-01-01T12:00:00Z",
        "service": "Model Service"
    }
    """
    try:
        if model is None:
            return jsonify({
                'error': 'Model not available',
                'message': 'Fraud detection model is not loaded'
            }), 503
        
        data = request.get_json()
        if not data or 'transactions' not in data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request must contain "transactions" array'
            }), 400
        
        transactions = data['transactions']
        if not isinstance(transactions, list) or len(transactions) == 0:
            return jsonify({
                'error': 'Invalid transactions',
                'message': 'Transactions must be a non-empty array'
            }), 400
        
        results = []
        
        for transaction in transactions:
            try:
                # Validate transaction
                if not validate_transaction(transaction):
                    results.append({
                        'transaction_id': transaction.get('transaction_id', 'unknown'),
                        'error': 'Invalid transaction data',
                        'risk': None,
                        'prediction': None
                    })
                    continue
                
                # Preprocess transaction
                processed_df = preprocess_transaction(transaction)
                
                # Make prediction
                prediction_proba = model.predict_proba(processed_df)[0]
                fraud_probability = prediction_proba[1] if len(prediction_proba) > 1 else prediction_proba[0]
                prediction = int(fraud_probability >= 0.5)
                
                results.append({
                    'transaction_id': transaction.get('transaction_id', f'tx_{len(results)}'),
                    'risk': float(fraud_probability),
                    'prediction': prediction,
                    'confidence': float(max(prediction_proba))
                })
                
            except Exception as e:
                logger.error(f"Error processing transaction: {str(e)}")
                results.append({
                    'transaction_id': transaction.get('transaction_id', 'unknown'),
                    'error': f'Processing error: {str(e)}',
                    'risk': None,
                    'prediction': None
                })
        
        response = {
            'results': results,
            'processed_at': datetime.utcnow().isoformat(),
            'service': 'Model Service',
            'model_version': '1.0.0'
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Unexpected error in score_transactions: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/model/info', methods=['GET'])
def model_info():
    """Get information about the loaded model."""
    if model is None:
        return jsonify({
            'error': 'Model not loaded',
            'message': 'No model is currently loaded'
        }), 503
    
    info = {
        'model_type': type(model).__name__,
        'feature_columns': feature_columns,
        'loaded_at': datetime.utcnow().isoformat(),
        'service': 'Model Service'
    }
    
    # Try to get additional model info if available
    try:
        if hasattr(model, 'n_features_in_'):
            info['n_features'] = model.n_features_in_
        if hasattr(model, 'classes_'):
            info['classes'] = model.classes_.tolist()
    except:
        pass
    
    return jsonify(info)

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
    logger.info("Starting FraudShield Model Service...")
    
    # Load the model
    if not load_model():
        logger.error("Failed to load model. Exiting.")
        sys.exit(1)
    
    # Start the Flask app
    logger.info("Model Service starting on port 8001...")
    app.run(host='0.0.0.0', port=8001, debug=False)
