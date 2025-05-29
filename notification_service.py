#!/usr/bin/env python3
"""
FraudShield Notification Service
Handles real-time alerts, notifications, and communication.
Runs on port 8004.
"""

import os
import json
import logging
import traceback
import smtplib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

# Configuration
NOTIFICATION_CONFIG = {
    'email': {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'username': os.getenv('EMAIL_USERNAME', ''),
        'password': os.getenv('EMAIL_PASSWORD', ''),
        'from_email': os.getenv('FROM_EMAIL', 'fraudshield@example.com')
    },
    'thresholds': {
        'high_risk': 0.8,
        'medium_risk': 0.5,
        'bulk_fraud_count': 5,
        'bulk_fraud_timeframe': 300  # 5 minutes
    }
}

class NotificationManager:
    """Manages different types of notifications and alerts."""
    
    def __init__(self):
        self.notification_history = []
        self.alert_rules = []
        self.subscribers = {
            'high_risk_alerts': [],
            'system_alerts': [],
            'daily_reports': []
        }
        self.recent_alerts = {}  # For rate limiting
    
    def add_subscriber(self, notification_type: str, contact: Dict[str, str]):
        """Add a subscriber to notification type."""
        if notification_type in self.subscribers:
            self.subscribers[notification_type].append(contact)
            return True
        return False
    
    def should_send_alert(self, alert_type: str, key: str) -> bool:
        """Check if alert should be sent (rate limiting)."""
        now = datetime.now()
        
        if alert_type not in self.recent_alerts:
            self.recent_alerts[alert_type] = {}
        
        if key in self.recent_alerts[alert_type]:
            last_sent = self.recent_alerts[alert_type][key]
            # Don't send same alert more than once per hour
            if (now - last_sent).seconds < 3600:
                return False
        
        self.recent_alerts[alert_type][key] = now
        return True
    
    def send_email(self, to_email: str, subject: str, body: str, html_body: str = None) -> bool:
        """Send email notification."""
        try:
            if not NOTIFICATION_CONFIG['email']['username']:
                logger.warning("Email not configured, skipping email notification")
                return False
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = NOTIFICATION_CONFIG['email']['from_email']
            msg['To'] = to_email
            
            # Add text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(NOTIFICATION_CONFIG['email']['smtp_server'], 
                            NOTIFICATION_CONFIG['email']['smtp_port']) as server:
                server.starttls()
                server.login(NOTIFICATION_CONFIG['email']['username'], 
                           NOTIFICATION_CONFIG['email']['password'])
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def create_fraud_alert_email(self, transaction: Dict[str, Any], risk_score: float) -> tuple:
        """Create fraud alert email content."""
        subject = f"🚨 High Risk Transaction Alert - Risk Score: {risk_score:.2%}"
        
        text_body = f"""
FRAUD ALERT - HIGH RISK TRANSACTION DETECTED

Transaction Details:
- Transaction ID: {transaction.get('transaction_id', 'N/A')}
- Type: {transaction.get('type', 'N/A')}
- Amount: ${transaction.get('amount', 0):,.2f}
- Risk Score: {risk_score:.2%}
- From Account: {transaction.get('nameOrig', 'N/A')}
- To Account: {transaction.get('nameDest', 'N/A')}
- Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This transaction has been flagged as high risk and requires immediate attention.

Please review the transaction details and take appropriate action.

FraudShield Security Team
        """
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="background-color: #fee2e2; border: 1px solid #fca5a5; padding: 20px; border-radius: 8px;">
                <h2 style="color: #dc2626; margin-top: 0;">🚨 High Risk Transaction Alert</h2>
                
                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #374151; margin-top: 0;">Transaction Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 5px; font-weight: bold;">Transaction ID:</td><td style="padding: 5px;">{transaction.get('transaction_id', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Type:</td><td style="padding: 5px;">{transaction.get('type', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Amount:</td><td style="padding: 5px;">${transaction.get('amount', 0):,.2f}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Risk Score:</td><td style="padding: 5px; color: #dc2626; font-weight: bold;">{risk_score:.2%}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">From Account:</td><td style="padding: 5px;">{transaction.get('nameOrig', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">To Account:</td><td style="padding: 5px;">{transaction.get('nameDest', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Timestamp:</td><td style="padding: 5px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                    </table>
                </div>
                
                <p style="color: #374151;">This transaction has been flagged as high risk and requires immediate attention.</p>
                <p style="color: #374151;">Please review the transaction details and take appropriate action.</p>
                
                <hr style="margin: 20px 0;">
                <p style="color: #6b7280; font-size: 12px;">FraudShield Security Team</p>
            </div>
        </body>
        </html>
        """
        
        return subject, text_body, html_body
    
    def send_fraud_alert(self, transaction: Dict[str, Any], risk_score: float) -> Dict[str, Any]:
        """Send fraud alert notifications."""
        try:
            alert_key = f"fraud_{transaction.get('transaction_id', 'unknown')}"
            
            if not self.should_send_alert('fraud', alert_key):
                return {
                    'status': 'skipped',
                    'message': 'Alert rate limited'
                }
            
            subject, text_body, html_body = self.create_fraud_alert_email(transaction, risk_score)
            
            # Send to high risk alert subscribers
            sent_count = 0
            failed_count = 0
            
            for subscriber in self.subscribers['high_risk_alerts']:
                if subscriber.get('type') == 'email':
                    if self.send_email(subscriber['contact'], subject, text_body, html_body):
                        sent_count += 1
                    else:
                        failed_count += 1
            
            # Log the alert
            alert_record = {
                'type': 'fraud_alert',
                'transaction_id': transaction.get('transaction_id'),
                'risk_score': risk_score,
                'sent_count': sent_count,
                'failed_count': failed_count,
                'timestamp': datetime.now().isoformat()
            }
            
            self.notification_history.append(alert_record)
            
            return {
                'status': 'sent',
                'sent_count': sent_count,
                'failed_count': failed_count,
                'alert_record': alert_record
            }
            
        except Exception as e:
            logger.error(f"Error sending fraud alert: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def send_system_alert(self, alert_type: str, message: str, details: Dict = None) -> Dict[str, Any]:
        """Send system alert notifications."""
        try:
            alert_key = f"system_{alert_type}"
            
            if not self.should_send_alert('system', alert_key):
                return {
                    'status': 'skipped',
                    'message': 'Alert rate limited'
                }
            
            subject = f"🔧 FraudShield System Alert: {alert_type.title()}"
            
            text_body = f"""
SYSTEM ALERT

Alert Type: {alert_type}
Message: {message}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{f'Details: {json.dumps(details, indent=2)}' if details else ''}

Please check the system status and take appropriate action if needed.

FraudShield System Monitor
            """
            
            # Send to system alert subscribers
            sent_count = 0
            failed_count = 0
            
            for subscriber in self.subscribers['system_alerts']:
                if subscriber.get('type') == 'email':
                    if self.send_email(subscriber['contact'], subject, text_body):
                        sent_count += 1
                    else:
                        failed_count += 1
            
            # Log the alert
            alert_record = {
                'type': 'system_alert',
                'alert_type': alert_type,
                'message': message,
                'details': details,
                'sent_count': sent_count,
                'failed_count': failed_count,
                'timestamp': datetime.now().isoformat()
            }
            
            self.notification_history.append(alert_record)
            
            return {
                'status': 'sent',
                'sent_count': sent_count,
                'failed_count': failed_count,
                'alert_record': alert_record
            }
            
        except Exception as e:
            logger.error(f"Error sending system alert: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_notification_history(self, limit: int = 100) -> List[Dict]:
        """Get notification history."""
        return self.notification_history[-limit:]
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        total_notifications = len(self.notification_history)
        
        if total_notifications == 0:
            return {
                'total_notifications': 0,
                'fraud_alerts': 0,
                'system_alerts': 0,
                'success_rate': 0
            }
        
        fraud_alerts = len([n for n in self.notification_history if n['type'] == 'fraud_alert'])
        system_alerts = len([n for n in self.notification_history if n['type'] == 'system_alert'])
        
        total_sent = sum(n.get('sent_count', 0) for n in self.notification_history)
        total_failed = sum(n.get('failed_count', 0) for n in self.notification_history)
        total_attempts = total_sent + total_failed
        
        success_rate = (total_sent / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            'total_notifications': total_notifications,
            'fraud_alerts': fraud_alerts,
            'system_alerts': system_alerts,
            'total_sent': total_sent,
            'total_failed': total_failed,
            'success_rate': round(success_rate, 2),
            'subscribers': {
                'high_risk_alerts': len(self.subscribers['high_risk_alerts']),
                'system_alerts': len(self.subscribers['system_alerts']),
                'daily_reports': len(self.subscribers['daily_reports'])
            }
        }

# Initialize notification manager
notification_manager = NotificationManager()

# Add default subscribers (in production, load from database)
notification_manager.add_subscriber('high_risk_alerts', {
    'type': 'email',
    'contact': 'security@example.com',
    'name': 'Security Team'
})

notification_manager.add_subscriber('system_alerts', {
    'type': 'email',
    'contact': 'admin@example.com',
    'name': 'System Admin'
})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Notification Service',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'email_configured': bool(NOTIFICATION_CONFIG['email']['username']),
        'subscribers': {
            'high_risk_alerts': len(notification_manager.subscribers['high_risk_alerts']),
            'system_alerts': len(notification_manager.subscribers['system_alerts'])
        }
    })

@app.route('/fraud-alert', methods=['POST'])
def send_fraud_alert():
    """Send fraud alert notification."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        transaction = data.get('transaction', {})
        risk_score = data.get('risk_score', 0)
        
        if risk_score < NOTIFICATION_CONFIG['thresholds']['high_risk']:
            return jsonify({
                'status': 'skipped',
                'message': f'Risk score {risk_score:.2%} below threshold {NOTIFICATION_CONFIG["thresholds"]["high_risk"]:.2%}'
            })
        
        result = notification_manager.send_fraud_alert(transaction, risk_score)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error sending fraud alert: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/system-alert', methods=['POST'])
def send_system_alert():
    """Send system alert notification."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        alert_type = data.get('alert_type', 'unknown')
        message = data.get('message', '')
        details = data.get('details')
        
        result = notification_manager.send_system_alert(alert_type, message, details)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error sending system alert: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/subscribers', methods=['POST'])
def add_subscriber():
    """Add a new subscriber."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        notification_type = data.get('notification_type')
        contact = data.get('contact', {})
        
        if notification_manager.add_subscriber(notification_type, contact):
            return jsonify({
                'status': 'success',
                'message': 'Subscriber added successfully'
            })
        else:
            return jsonify({'error': 'Invalid notification type'}), 400
            
    except Exception as e:
        logger.error(f"Error adding subscriber: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/history', methods=['GET'])
def get_notification_history():
    """Get notification history."""
    try:
        limit = int(request.args.get('limit', 100))
        history = notification_manager.get_notification_history(limit)
        return jsonify({
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        logger.error(f"Error getting notification history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_notification_stats():
    """Get notification statistics."""
    try:
        stats = notification_manager.get_notification_stats()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting notification stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting FraudShield Notification Service...")
    logger.info(f"Email configured: {bool(NOTIFICATION_CONFIG['email']['username'])}")
    logger.info("Notification Service starting on port 8004...")
    app.run(host='0.0.0.0', port=8004, debug=False)
