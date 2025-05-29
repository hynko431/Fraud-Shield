# FraudShield - Advanced Fraud Detection System

FraudShield is a comprehensive real-time transaction fraud detection system with a modern web interface and robust backend services.

DataSet link :- https://drive.usercontent.google.com/download?id=1VNpyNkGxHdskfdTNRSjjyNa5qC9u0JyV&export=download&authuser=0
## 🏗️ Architecture

The system consists of three main components:

1. **Frontend Web Application** (`ap.html`) - Interactive web interface for testing fraud detection
2. **Model Service** (`model_service.py`) - Core fraud detection ML model service (Port 8001)
3. **Ingest Service** (`ingest_service.py`) - Transaction ingestion and data management (Port 9001)

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Choose Your Setup**

   **Option A: Basic Setup (Recommended for Testing)**
   ```bash
   python start_basic.py
   ```
   Starts essential services only (Model + Ingest + Frontend)

   **Option B: Full Integration (Complete System)**
   ```bash
   python integrated_startup.py
   ```
   Starts all services with API Gateway

   **Option C: Manual Service Management**
   ```bash
   python start_services.py
   ```
   Original startup script for individual service control

3. **Access the Application**
   - The web browser will open automatically to: http://localhost:8080/ap.html
   - Or manually navigate to the URL above

## 🔗 Frontend-Backend Integration

The system now features **fully integrated frontend and backend** with:

- ✅ **Intelligent Service Discovery**: Automatic detection of available services
- ✅ **Graceful Fallback**: API Gateway → Direct Services → Error Handling
- ✅ **Real-time Health Monitoring**: Live service status indicators
- ✅ **Flexible Configuration**: Switch between Gateway and Direct modes
- ✅ **Enhanced Error Handling**: Detailed error messages and retry logic
- ✅ **Unified Authentication**: API key-based security (when using Gateway)

### Integration Modes

**Direct Service Mode (Default)**
- Frontend communicates directly with backend services
- Faster for development and testing
- Minimal setup required

**API Gateway Mode**
- All requests routed through centralized gateway
- Enhanced security and rate limiting
- Better for production deployments

See `INTEGRATION_GUIDE.md` for detailed integration documentation.

## 🔧 Manual Service Management

### Start Individual Services

**Model Service (Port 8001):**
```bash
python model_service.py
```

**Ingest Service (Port 9001):**
```bash
python ingest_service.py
```

### Service Health Checks

- Model Service: http://localhost:8001/health
- Ingest Service: http://localhost:9001/health

## 📊 Features

### Frontend Features
- ✅ Real-time fraud risk scoring
- ✅ Interactive transaction form with validation
- ✅ Service health monitoring
- ✅ Transaction history with local storage
- ✅ Enhanced error handling with fallback mechanisms
- ✅ Visual risk indicators (Low/Medium/High)
- ✅ Dark mode support
- ✅ Responsive design

### Backend Features
- ✅ RESTful API endpoints
- ✅ Machine learning model integration
- ✅ Transaction data validation
- ✅ Automatic service health monitoring
- ✅ Transaction storage and retrieval
- ✅ CSV export functionality
- ✅ Comprehensive error handling
- ✅ CORS support for frontend integration

## 🔌 API Endpoints

### Model Service (Port 8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/score` | POST | Score transactions for fraud risk |
| `/model/info` | GET | Get model information |

### Ingest Service (Port 9001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/score` | POST | Score transactions (forwards to Model Service) |
| `/ingest` | POST | Store individual transactions |
| `/transactions` | GET | Retrieve stored transactions |
| `/stats` | GET | Get transaction statistics |
| `/export` | GET | Export transactions as CSV |

## 📝 API Usage Examples

### Score a Transaction

```bash
curl -X POST http://localhost:8001/score \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [{
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
    }]
  }'
```

### Store a Transaction

```bash
curl -X POST http://localhost:9001/ingest \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

## 🎯 Transaction Data Format

The system expects transactions in the following format:

```json
{
  "transaction_id": "unique_identifier",
  "step": 1,
  "type": "PAYMENT|TRANSFER|CASH_OUT|DEBIT",
  "amount": 1000.0,
  "nameOrig": "C123456789",
  "oldbalanceOrg": 5000.0,
  "newbalanceOrig": 4000.0,
  "nameDest": "M987654321",
  "oldbalanceDest": 0.0,
  "newbalanceDest": 0.0
}
```

### Field Descriptions

- `transaction_id`: Unique identifier for the transaction
- `step`: Transaction step/sequence number
- `type`: Transaction type (PAYMENT, TRANSFER, CASH_OUT, DEBIT)
- `amount`: Transaction amount
- `nameOrig`: Origin account (format: C + 9 digits)
- `oldbalanceOrg`: Origin account balance before transaction
- `newbalanceOrig`: Origin account balance after transaction
- `nameDest`: Destination account (format: M/C + 9 digits)
- `oldbalanceDest`: Destination account balance before transaction
- `newbalanceDest`: Destination account balance after transaction

## 🔍 Risk Scoring

The system returns fraud risk scores as follows:

- **Low Risk (0-49%)**: Transaction appears legitimate
- **Medium Risk (50-79%)**: Transaction shows suspicious patterns
- **High Risk (80-100%)**: Highly suspicious, likely fraudulent

## 🛠️ Troubleshooting

### Common Issues

1. **Services won't start**
   - Check if ports 8001 and 9001 are available
   - Ensure `fraud_detection_model.pkl` exists
   - Verify Python dependencies are installed

2. **Frontend can't connect to services**
   - Check service health endpoints
   - Verify CORS is enabled
   - Check browser console for errors

3. **Model loading errors**
   - Ensure `fraud_detection_model.pkl` is in the correct format
   - Check Python version compatibility
   - Verify scikit-learn version matches training environment

### Logs

Services log to console with timestamps. Use the startup script for centralized logging:

```bash
python start_services.py 2>&1 | tee fraudshield.log
```

## 📁 File Structure

```
FraudShield/
├── ap.html                     # Frontend web application
├── model_service.py           # Model Service backend
├── ingest_service.py          # Ingest Service backend
├── start_services.py          # Service startup script
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── fraud_detection_model.pkl  # Trained ML model
├── fraud_detection_samples.csv # Sample data
├── fraud_detection_predictions.csv # Predictions
└── transaction_storage/       # Transaction storage directory
```

## 🔒 Security Considerations

- Services run on localhost by default
- No authentication implemented (demo purposes)
- CORS enabled for frontend integration
- Input validation on all endpoints
- Error messages sanitized

## 🚀 Production Deployment

For production deployment, consider:

1. **Security**: Add authentication and authorization
2. **Database**: Replace file storage with proper database
3. **Monitoring**: Add comprehensive logging and monitoring
4. **Scaling**: Use load balancers and multiple service instances
5. **HTTPS**: Enable SSL/TLS encryption
6. **Environment**: Use environment variables for configuration

## 📄 License

This project is for demonstration purposes. Please ensure compliance with your organization's policies before production use.
