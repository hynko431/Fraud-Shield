#!/usr/bin/env python3
"""
FraudShield Analytics Service
Provides advanced analytics, reporting, and insights for fraud detection.
Runs on port 8002.
"""

import os
import json
import logging
import traceback
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import pandas as pd
import numpy as np
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
DATABASE_SERVICE_URL = 'http://localhost:8003'

class AnalyticsEngine:
    """Advanced analytics engine for fraud detection insights."""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data if still valid."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now().timestamp() - timestamp < self.cache_ttl:
                return data
        return None
    
    def set_cached_data(self, key: str, data: Any):
        """Cache data with timestamp."""
        self.cache[key] = (data, datetime.now().timestamp())
    
    def get_database_data(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Fetch data from database service."""
        try:
            response = requests.get(
                f"{DATABASE_SERVICE_URL}/{endpoint}",
                params=params or {},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Database service error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch data from database: {str(e)}")
            return None
    
    def calculate_fraud_trends(self, days: int = 30) -> Dict[str, Any]:
        """Calculate fraud trends over time."""
        cache_key = f"fraud_trends_{days}"
        cached = self.get_cached_data(cache_key)
        if cached:
            return cached
        
        try:
            # Get predictions from last N days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            predictions_data = self.get_database_data('predictions', {
                'limit': 10000,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            })
            
            if not predictions_data or not predictions_data.get('predictions'):
                return {'error': 'No prediction data available'}
            
            df = pd.DataFrame(predictions_data['predictions'])
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['date'] = df['created_at'].dt.date
            
            # Calculate daily statistics
            daily_stats = df.groupby('date').agg({
                'risk_score': ['mean', 'std', 'count'],
                'prediction': ['sum', 'count']
            }).round(4)
            
            daily_stats.columns = ['avg_risk', 'risk_std', 'total_transactions', 
                                  'fraud_count', 'total_count']
            daily_stats['fraud_rate'] = (daily_stats['fraud_count'] / 
                                       daily_stats['total_count']).round(4)
            
            # Convert to list of dictionaries
            trends = []
            for date, row in daily_stats.iterrows():
                trends.append({
                    'date': date.isoformat(),
                    'avg_risk_score': float(row['avg_risk']),
                    'risk_std': float(row['risk_std']) if not pd.isna(row['risk_std']) else 0,
                    'total_transactions': int(row['total_transactions']),
                    'fraud_count': int(row['fraud_count']),
                    'fraud_rate': float(row['fraud_rate'])
                })
            
            result = {
                'trends': trends,
                'summary': {
                    'total_days': len(trends),
                    'avg_daily_transactions': float(daily_stats['total_transactions'].mean()),
                    'avg_fraud_rate': float(daily_stats['fraud_rate'].mean()),
                    'peak_fraud_rate': float(daily_stats['fraud_rate'].max()),
                    'lowest_fraud_rate': float(daily_stats['fraud_rate'].min())
                }
            }
            
            self.set_cached_data(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error calculating fraud trends: {str(e)}")
            return {'error': str(e)}
    
    def analyze_transaction_patterns(self) -> Dict[str, Any]:
        """Analyze transaction patterns and anomalies."""
        cache_key = "transaction_patterns"
        cached = self.get_cached_data(cache_key)
        if cached:
            return cached
        
        try:
            # Get recent transactions
            transactions_data = self.get_database_data('transactions', {'limit': 5000})
            
            if not transactions_data or not transactions_data.get('transactions'):
                return {'error': 'No transaction data available'}
            
            df = pd.DataFrame(transactions_data['transactions'])
            
            # Analyze by transaction type
            type_analysis = df.groupby('type').agg({
                'amount': ['mean', 'median', 'std', 'count'],
                'oldbalanceOrg': 'mean',
                'newbalanceOrig': 'mean'
            }).round(2)
            
            type_analysis.columns = ['avg_amount', 'median_amount', 'amount_std', 
                                   'count', 'avg_old_balance', 'avg_new_balance']
            
            # Analyze amount distributions
            amount_percentiles = df['amount'].quantile([0.25, 0.5, 0.75, 0.9, 0.95, 0.99]).to_dict()
            
            # Detect potential anomalies (high amounts)
            q99 = df['amount'].quantile(0.99)
            high_amount_transactions = df[df['amount'] > q99]
            
            result = {
                'transaction_types': type_analysis.to_dict('index'),
                'amount_distribution': {
                    'percentiles': {f"p{int(k*100)}": float(v) for k, v in amount_percentiles.items()},
                    'mean': float(df['amount'].mean()),
                    'std': float(df['amount'].std())
                },
                'anomalies': {
                    'high_amount_threshold': float(q99),
                    'high_amount_count': len(high_amount_transactions),
                    'high_amount_transactions': high_amount_transactions.head(10).to_dict('records')
                },
                'summary': {
                    'total_transactions': len(df),
                    'unique_types': df['type'].nunique(),
                    'date_range': {
                        'start': df['created_at'].min(),
                        'end': df['created_at'].max()
                    }
                }
            }
            
            self.set_cached_data(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing transaction patterns: {str(e)}")
            return {'error': str(e)}
    
    def generate_risk_distribution(self) -> Dict[str, Any]:
        """Generate risk score distribution analysis."""
        cache_key = "risk_distribution"
        cached = self.get_cached_data(cache_key)
        if cached:
            return cached
        
        try:
            predictions_data = self.get_database_data('predictions', {'limit': 10000})
            
            if not predictions_data or not predictions_data.get('predictions'):
                return {'error': 'No prediction data available'}
            
            df = pd.DataFrame(predictions_data['predictions'])
            
            # Create risk score bins
            bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            labels = ['0.0-0.1', '0.1-0.2', '0.2-0.3', '0.3-0.4', '0.4-0.5',
                     '0.5-0.6', '0.6-0.7', '0.7-0.8', '0.8-0.9', '0.9-1.0']
            
            df['risk_bin'] = pd.cut(df['risk_score'], bins=bins, labels=labels, include_lowest=True)
            
            # Count distribution
            distribution = df['risk_bin'].value_counts().sort_index()
            
            # Calculate statistics by risk level
            low_risk = df[df['risk_score'] < 0.5]
            medium_risk = df[(df['risk_score'] >= 0.5) & (df['risk_score'] < 0.8)]
            high_risk = df[df['risk_score'] >= 0.8]
            
            result = {
                'distribution': {
                    'bins': [{'range': label, 'count': int(count)} 
                            for label, count in distribution.items()],
                    'total_predictions': len(df)
                },
                'risk_levels': {
                    'low_risk': {
                        'count': len(low_risk),
                        'percentage': float(len(low_risk) / len(df) * 100),
                        'avg_score': float(low_risk['risk_score'].mean()) if len(low_risk) > 0 else 0
                    },
                    'medium_risk': {
                        'count': len(medium_risk),
                        'percentage': float(len(medium_risk) / len(df) * 100),
                        'avg_score': float(medium_risk['risk_score'].mean()) if len(medium_risk) > 0 else 0
                    },
                    'high_risk': {
                        'count': len(high_risk),
                        'percentage': float(len(high_risk) / len(df) * 100),
                        'avg_score': float(high_risk['risk_score'].mean()) if len(high_risk) > 0 else 0
                    }
                },
                'statistics': {
                    'mean_risk_score': float(df['risk_score'].mean()),
                    'median_risk_score': float(df['risk_score'].median()),
                    'std_risk_score': float(df['risk_score'].std()),
                    'min_risk_score': float(df['risk_score'].min()),
                    'max_risk_score': float(df['risk_score'].max())
                }
            }
            
            self.set_cached_data(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error generating risk distribution: {str(e)}")
            return {'error': str(e)}
    
    def get_model_performance_metrics(self) -> Dict[str, Any]:
        """Calculate model performance metrics."""
        try:
            predictions_data = self.get_database_data('predictions', {'limit': 10000})
            
            if not predictions_data or not predictions_data.get('predictions'):
                return {'error': 'No prediction data available'}
            
            df = pd.DataFrame(predictions_data['predictions'])
            
            # Basic metrics
            total_predictions = len(df)
            fraud_predictions = len(df[df['prediction'] == 1])
            legitimate_predictions = len(df[df['prediction'] == 0])
            
            # Risk score statistics
            avg_risk_score = df['risk_score'].mean()
            high_risk_count = len(df[df['risk_score'] >= 0.8])
            medium_risk_count = len(df[(df['risk_score'] >= 0.5) & (df['risk_score'] < 0.8)])
            low_risk_count = len(df[df['risk_score'] < 0.5])
            
            # Service usage statistics
            service_usage = df['service_used'].value_counts().to_dict() if 'service_used' in df.columns else {}
            
            return {
                'total_predictions': total_predictions,
                'fraud_predictions': fraud_predictions,
                'legitimate_predictions': legitimate_predictions,
                'fraud_rate': float(fraud_predictions / total_predictions) if total_predictions > 0 else 0,
                'risk_statistics': {
                    'average_risk_score': float(avg_risk_score),
                    'high_risk_count': high_risk_count,
                    'medium_risk_count': medium_risk_count,
                    'low_risk_count': low_risk_count,
                    'high_risk_percentage': float(high_risk_count / total_predictions * 100) if total_predictions > 0 else 0
                },
                'service_usage': service_usage,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating model performance: {str(e)}")
            return {'error': str(e)}

# Initialize analytics engine
analytics_engine = AnalyticsEngine()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Analytics Service',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'database_service': DATABASE_SERVICE_URL
    })

@app.route('/fraud-trends', methods=['GET'])
def get_fraud_trends():
    """Get fraud trends over time."""
    try:
        days = int(request.args.get('days', 30))
        trends = analytics_engine.calculate_fraud_trends(days)
        return jsonify(trends)
    except Exception as e:
        logger.error(f"Error getting fraud trends: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/transaction-patterns', methods=['GET'])
def get_transaction_patterns():
    """Get transaction pattern analysis."""
    try:
        patterns = analytics_engine.analyze_transaction_patterns()
        return jsonify(patterns)
    except Exception as e:
        logger.error(f"Error getting transaction patterns: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/risk-distribution', methods=['GET'])
def get_risk_distribution():
    """Get risk score distribution."""
    try:
        distribution = analytics_engine.generate_risk_distribution()
        return jsonify(distribution)
    except Exception as e:
        logger.error(f"Error getting risk distribution: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/model-performance', methods=['GET'])
def get_model_performance():
    """Get model performance metrics."""
    try:
        performance = analytics_engine.get_model_performance_metrics()
        return jsonify(performance)
    except Exception as e:
        logger.error(f"Error getting model performance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard-summary', methods=['GET'])
def get_dashboard_summary():
    """Get comprehensive dashboard summary."""
    try:
        summary = {
            'fraud_trends': analytics_engine.calculate_fraud_trends(7),  # Last 7 days
            'risk_distribution': analytics_engine.generate_risk_distribution(),
            'model_performance': analytics_engine.get_model_performance_metrics(),
            'generated_at': datetime.utcnow().isoformat()
        }
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting FraudShield Analytics Service...")
    logger.info(f"Database Service URL: {DATABASE_SERVICE_URL}")
    logger.info("Analytics Service starting on port 8002...")
    app.run(host='0.0.0.0', port=8002, debug=False)
