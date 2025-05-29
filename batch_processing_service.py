#!/usr/bin/env python3
"""
FraudShield Batch Processing Service
Handles bulk transaction processing, scheduled tasks, and batch analytics.
Runs on port 8005.
"""

import os
import json
import logging
import traceback
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import time

import pandas as pd
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
SERVICE_URLS = {
    'model': 'http://localhost:8001',
    'database': 'http://localhost:8003',
    'notification': 'http://localhost:8004'
}

BATCH_CONFIG = {
    'max_batch_size': 1000,
    'processing_timeout': 300,  # 5 minutes
    'retry_attempts': 3,
    'retry_delay': 5  # seconds
}

class BatchProcessor:
    """Handles batch processing operations."""
    
    def __init__(self):
        self.active_jobs = {}
        self.job_history = []
        self.job_counter = 0
    
    def generate_job_id(self) -> str:
        """Generate unique job ID."""
        self.job_counter += 1
        return f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.job_counter}"
    
    def create_job(self, job_type: str, data: Dict[str, Any]) -> str:
        """Create a new batch job."""
        job_id = self.generate_job_id()
        
        job = {
            'job_id': job_id,
            'job_type': job_type,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'progress': 0,
            'total_items': 0,
            'processed_items': 0,
            'failed_items': 0,
            'results': {},
            'error_message': None,
            'data': data
        }
        
        self.active_jobs[job_id] = job
        logger.info(f"Created batch job {job_id} of type {job_type}")
        
        return job_id
    
    def update_job_progress(self, job_id: str, processed: int, total: int, results: Dict = None):
        """Update job progress."""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job['processed_items'] = processed
            job['total_items'] = total
            job['progress'] = (processed / total * 100) if total > 0 else 0
            
            if results:
                job['results'].update(results)
    
    def complete_job(self, job_id: str, success: bool = True, error_message: str = None):
        """Mark job as completed."""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job['status'] = 'completed' if success else 'failed'
            job['completed_at'] = datetime.now().isoformat()
            job['error_message'] = error_message
            
            # Move to history
            self.job_history.append(job.copy())
            
            # Keep only last 100 jobs in history
            if len(self.job_history) > 100:
                self.job_history = self.job_history[-100:]
            
            # Remove from active jobs
            del self.active_jobs[job_id]
            
            logger.info(f"Job {job_id} completed with status: {job['status']}")
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status."""
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]
        
        # Check history
        for job in self.job_history:
            if job['job_id'] == job_id:
                return job
        
        return None
    
    def process_transactions_batch(self, job_id: str, transactions: List[Dict]) -> Dict[str, Any]:
        """Process a batch of transactions."""
        try:
            job = self.active_jobs[job_id]
            job['status'] = 'running'
            job['started_at'] = datetime.now().isoformat()
            job['total_items'] = len(transactions)
            
            results = {
                'processed': 0,
                'failed': 0,
                'high_risk_count': 0,
                'predictions': [],
                'errors': []
            }
            
            # Process in smaller chunks
            chunk_size = min(100, len(transactions))
            
            for i in range(0, len(transactions), chunk_size):
                chunk = transactions[i:i + chunk_size]
                
                try:
                    # Send to model service
                    response = requests.post(
                        f"{SERVICE_URLS['model']}/score",
                        json={'transactions': chunk},
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        chunk_results = response.json()
                        
                        for result in chunk_results.get('results', []):
                            results['predictions'].append(result)
                            
                            if result.get('risk', 0) >= 0.8:
                                results['high_risk_count'] += 1
                        
                        results['processed'] += len(chunk)
                        
                        # Store predictions in database
                        for prediction in chunk_results.get('results', []):
                            try:
                                requests.post(
                                    f"{SERVICE_URLS['database']}/predictions",
                                    json={'prediction': prediction},
                                    timeout=30
                                )
                            except Exception as e:
                                logger.warning(f"Failed to store prediction: {str(e)}")
                    
                    else:
                        results['failed'] += len(chunk)
                        results['errors'].append(f"Chunk {i//chunk_size + 1}: HTTP {response.status_code}")
                
                except Exception as e:
                    results['failed'] += len(chunk)
                    results['errors'].append(f"Chunk {i//chunk_size + 1}: {str(e)}")
                
                # Update progress
                self.update_job_progress(job_id, results['processed'] + results['failed'], len(transactions))
                
                # Small delay to prevent overwhelming services
                time.sleep(0.1)
            
            # Send high-risk alerts if needed
            if results['high_risk_count'] > 0:
                try:
                    requests.post(
                        f"{SERVICE_URLS['notification']}/system-alert",
                        json={
                            'alert_type': 'batch_high_risk',
                            'message': f"Batch processing found {results['high_risk_count']} high-risk transactions",
                            'details': {
                                'job_id': job_id,
                                'total_processed': results['processed'],
                                'high_risk_count': results['high_risk_count']
                            }
                        },
                        timeout=30
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification: {str(e)}")
            
            self.complete_job(job_id, success=True)
            return results
            
        except Exception as e:
            logger.error(f"Batch processing failed for job {job_id}: {str(e)}")
            self.complete_job(job_id, success=False, error_message=str(e))
            raise
    
    def process_csv_file(self, job_id: str, file_path: str) -> Dict[str, Any]:
        """Process transactions from CSV file."""
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Convert to transaction format
            transactions = []
            for _, row in df.iterrows():
                transaction = {
                    'transaction_id': f"csv_{job_id}_{len(transactions)}",
                    'step': int(row.get('step', 1)),
                    'type': str(row.get('type', 'PAYMENT')),
                    'amount': float(row.get('amount', 0)),
                    'nameOrig': str(row.get('nameOrig', '')),
                    'oldbalanceOrg': float(row.get('oldbalanceOrg', 0)),
                    'newbalanceOrig': float(row.get('newbalanceOrig', 0)),
                    'nameDest': str(row.get('nameDest', '')),
                    'oldbalanceDest': float(row.get('oldbalanceDest', 0)),
                    'newbalanceDest': float(row.get('newbalanceDest', 0))
                }
                transactions.append(transaction)
            
            # Process the transactions
            return self.process_transactions_batch(job_id, transactions)
            
        except Exception as e:
            logger.error(f"CSV processing failed for job {job_id}: {str(e)}")
            self.complete_job(job_id, success=False, error_message=str(e))
            raise

# Initialize batch processor
batch_processor = BatchProcessor()

def run_batch_job(job_id: str, job_type: str, data: Dict[str, Any]):
    """Run batch job in background thread."""
    try:
        if job_type == 'process_transactions':
            transactions = data.get('transactions', [])
            batch_processor.process_transactions_batch(job_id, transactions)
        
        elif job_type == 'process_csv':
            file_path = data.get('file_path')
            batch_processor.process_csv_file(job_id, file_path)
        
        else:
            batch_processor.complete_job(job_id, success=False, error_message=f"Unknown job type: {job_type}")
    
    except Exception as e:
        logger.error(f"Batch job {job_id} failed: {str(e)}")
        batch_processor.complete_job(job_id, success=False, error_message=str(e))

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Batch Processing Service',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'active_jobs': len(batch_processor.active_jobs),
        'completed_jobs': len(batch_processor.job_history),
        'config': BATCH_CONFIG
    })

@app.route('/jobs', methods=['POST'])
def create_batch_job():
    """Create a new batch processing job."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        job_type = data.get('job_type')
        job_data = data.get('data', {})
        
        if not job_type:
            return jsonify({'error': 'job_type is required'}), 400
        
        # Validate job type and data
        if job_type == 'process_transactions':
            transactions = job_data.get('transactions', [])
            if not transactions:
                return jsonify({'error': 'transactions array is required'}), 400
            
            if len(transactions) > BATCH_CONFIG['max_batch_size']:
                return jsonify({
                    'error': f'Batch size exceeds maximum of {BATCH_CONFIG["max_batch_size"]}'
                }), 400
        
        elif job_type == 'process_csv':
            file_path = job_data.get('file_path')
            if not file_path or not Path(file_path).exists():
                return jsonify({'error': 'Valid file_path is required'}), 400
        
        else:
            return jsonify({'error': f'Unknown job type: {job_type}'}), 400
        
        # Create job
        job_id = batch_processor.create_job(job_type, job_data)
        
        # Start processing in background thread
        thread = threading.Thread(
            target=run_batch_job,
            args=(job_id, job_type, job_data),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'created',
            'message': 'Batch job created and started'
        })
        
    except Exception as e:
        logger.error(f"Error creating batch job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """Get status of a specific job."""
    try:
        job = batch_processor.get_job_status(job_id)
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify(job)
        
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/jobs', methods=['GET'])
def list_jobs():
    """List all jobs (active and completed)."""
    try:
        limit = int(request.args.get('limit', 50))
        status_filter = request.args.get('status')
        
        all_jobs = list(batch_processor.active_jobs.values()) + batch_processor.job_history
        
        # Filter by status if provided
        if status_filter:
            all_jobs = [job for job in all_jobs if job['status'] == status_filter]
        
        # Sort by creation time (newest first)
        all_jobs.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Apply limit
        all_jobs = all_jobs[:limit]
        
        return jsonify({
            'jobs': all_jobs,
            'count': len(all_jobs),
            'active_jobs': len(batch_processor.active_jobs),
            'completed_jobs': len(batch_processor.job_history)
        })
        
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/jobs/<job_id>', methods=['DELETE'])
def cancel_job(job_id: str):
    """Cancel an active job."""
    try:
        if job_id not in batch_processor.active_jobs:
            return jsonify({'error': 'Job not found or already completed'}), 404
        
        batch_processor.complete_job(job_id, success=False, error_message='Job cancelled by user')
        
        return jsonify({
            'status': 'cancelled',
            'message': f'Job {job_id} has been cancelled'
        })
        
    except Exception as e:
        logger.error(f"Error cancelling job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_batch_stats():
    """Get batch processing statistics."""
    try:
        all_jobs = list(batch_processor.active_jobs.values()) + batch_processor.job_history
        
        total_jobs = len(all_jobs)
        completed_jobs = len([j for j in all_jobs if j['status'] == 'completed'])
        failed_jobs = len([j for j in all_jobs if j['status'] == 'failed'])
        active_jobs = len([j for j in all_jobs if j['status'] in ['pending', 'running']])
        
        # Calculate processing statistics
        total_processed = sum(j.get('processed_items', 0) for j in all_jobs)
        total_failed = sum(j.get('failed_items', 0) for j in all_jobs)
        
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        return jsonify({
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'active_jobs': active_jobs,
            'success_rate': round(success_rate, 2),
            'total_items_processed': total_processed,
            'total_items_failed': total_failed,
            'average_batch_size': round(total_processed / completed_jobs) if completed_jobs > 0 else 0
        })
        
    except Exception as e:
        logger.error(f"Error getting batch stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting FraudShield Batch Processing Service...")
    logger.info(f"Service URLs: {SERVICE_URLS}")
    logger.info(f"Batch config: {BATCH_CONFIG}")
    logger.info("Batch Processing Service starting on port 8005...")
    app.run(host='0.0.0.0', port=8005, debug=False)
