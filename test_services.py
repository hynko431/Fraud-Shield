#!/usr/bin/env python3
"""
FraudShield Services Test Script
Tests all backend services to ensure they're working correctly.
"""

import requests
import json
import time
import sys
from datetime import datetime

# Service URLs
SERVICES = {
    'API Gateway': 'http://localhost:8000',
    'Model Service': 'http://localhost:8001',
    'Analytics Service': 'http://localhost:8002',
    'Database Service': 'http://localhost:8003',
    'Notification Service': 'http://localhost:8004',
    'Batch Processing Service': 'http://localhost:8005',
    'Monitoring Service': 'http://localhost:8006',
    'Ingest Service': 'http://localhost:9001'
}

# Test API key
API_KEY = 'fs_test_key_789'

def test_service_health(service_name, url):
    """Test if a service is healthy."""
    try:
        response = requests.get(f"{url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {service_name}: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ {service_name}: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {service_name}: Connection refused")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ {service_name}: Timeout")
        return False
    except Exception as e:
        print(f"❌ {service_name}: {str(e)}")
        return False

def test_transaction_scoring():
    """Test transaction scoring through API Gateway."""
    print("\n🧪 Testing Transaction Scoring...")
    
    test_transaction = {
        "transactions": [
            {
                "transaction_id": f"test_{int(time.time())}",
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
    
    try:
        # Test through API Gateway
        response = requests.post(
            f"{SERVICES['API Gateway']}/api/v1/score",
            json=test_transaction,
            headers={'X-API-Key': API_KEY},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            risk_score = result['results'][0]['risk']
            print(f"✅ Transaction scoring successful - Risk: {risk_score:.2%}")
            return True
        else:
            print(f"❌ Transaction scoring failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Transaction scoring error: {str(e)}")
        return False

def test_database_operations():
    """Test database operations."""
    print("\n🧪 Testing Database Operations...")
    
    test_transaction = {
        "transaction": {
            "transaction_id": f"db_test_{int(time.time())}",
            "step": 1,
            "type": "TRANSFER",
            "amount": 500.0,
            "nameOrig": "C987654321",
            "oldbalanceOrg": 2000.0,
            "newbalanceOrig": 1500.0,
            "nameDest": "C123456789",
            "oldbalanceDest": 1000.0,
            "newbalanceDest": 1500.0
        }
    }
    
    try:
        # Store transaction
        response = requests.post(
            f"{SERVICES['Database Service']}/transactions",
            json=test_transaction,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Database transaction storage successful")
            
            # Retrieve transactions
            response = requests.get(
                f"{SERVICES['Database Service']}/transactions?limit=5",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Database transaction retrieval successful - Count: {data['count']}")
                return True
            else:
                print(f"❌ Database retrieval failed: HTTP {response.status_code}")
                return False
        else:
            print(f"❌ Database storage failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Database operations error: {str(e)}")
        return False

def test_analytics():
    """Test analytics service."""
    print("\n🧪 Testing Analytics Service...")
    
    try:
        response = requests.get(
            f"{SERVICES['Analytics Service']}/model-performance",
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analytics service successful - Total predictions: {data.get('total_predictions', 0)}")
            return True
        else:
            print(f"❌ Analytics service failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Analytics service error: {str(e)}")
        return False

def test_monitoring():
    """Test monitoring service."""
    print("\n🧪 Testing Monitoring Service...")
    
    try:
        response = requests.get(
            f"{SERVICES['Monitoring Service']}/overview",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Monitoring service successful - System status: {data.get('system_status', 'unknown')}")
            return True
        else:
            print(f"❌ Monitoring service failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Monitoring service error: {str(e)}")
        return False

def test_batch_processing():
    """Test batch processing service."""
    print("\n🧪 Testing Batch Processing Service...")
    
    batch_job = {
        "job_type": "process_transactions",
        "data": {
            "transactions": [
                {
                    "transaction_id": f"batch_test_{int(time.time())}_1",
                    "step": 1,
                    "type": "CASH_OUT",
                    "amount": 2000.0,
                    "nameOrig": "C111111111",
                    "oldbalanceOrg": 3000.0,
                    "newbalanceOrig": 1000.0,
                    "nameDest": "C222222222",
                    "oldbalanceDest": 500.0,
                    "newbalanceDest": 2500.0
                }
            ]
        }
    }
    
    try:
        response = requests.post(
            f"{SERVICES['Batch Processing Service']}/jobs",
            json=batch_job,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            job_id = data['job_id']
            print(f"✅ Batch job created successfully - Job ID: {job_id}")
            
            # Wait a moment and check status
            time.sleep(2)
            
            response = requests.get(
                f"{SERVICES['Batch Processing Service']}/jobs/{job_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ Batch job status check successful - Status: {status_data.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Batch job status check failed: HTTP {response.status_code}")
                return False
        else:
            print(f"❌ Batch processing failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Batch processing error: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("🚀 FraudShield Services Test Suite")
    print("=" * 50)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test service health
    print("🏥 Testing Service Health...")
    health_results = []
    for service_name, url in SERVICES.items():
        result = test_service_health(service_name, url)
        health_results.append(result)
    
    healthy_services = sum(health_results)
    total_services = len(health_results)
    
    print(f"\n📊 Health Check Results: {healthy_services}/{total_services} services healthy")
    
    if healthy_services < total_services:
        print("⚠️  Some services are not healthy. Skipping functional tests.")
        print("   Please ensure all services are running before running tests.")
        sys.exit(1)
    
    # Run functional tests
    print("\n🔧 Running Functional Tests...")
    
    test_results = []
    
    # Test transaction scoring
    test_results.append(test_transaction_scoring())
    
    # Test database operations
    test_results.append(test_database_operations())
    
    # Test analytics
    test_results.append(test_analytics())
    
    # Test monitoring
    test_results.append(test_monitoring())
    
    # Test batch processing
    test_results.append(test_batch_processing())
    
    # Summary
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print(f"Services Health: {healthy_services}/{total_services}")
    print(f"Functional Tests: {passed_tests}/{total_tests}")
    
    if healthy_services == total_services and passed_tests == total_tests:
        print("🎉 All tests passed! FraudShield is working correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the logs and fix issues.")
        sys.exit(1)

if __name__ == '__main__':
    main()
