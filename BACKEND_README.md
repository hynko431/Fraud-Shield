# FraudShield Backend Services

A comprehensive microservices architecture for fraud detection with advanced analytics, monitoring, and real-time processing capabilities.

## 🏗️ Architecture Overview

FraudShield consists of 8 microservices that work together to provide a complete fraud detection solution:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │────│  API Gateway    │────│  Model Service  │
│   (Port 8080)   │    │   (Port 8000)   │    │   (Port 8001)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌────────┼────────┐
                       │        │        │
            ┌─────────────────┐ │ ┌─────────────────┐
            │  Analytics      │ │ │   Database      │
            │  (Port 8002)    │ │ │  (Port 8003)    │
            └─────────────────┘ │ └─────────────────┘
                       │        │        │
            ┌─────────────────┐ │ ┌─────────────────┐
            │ Notification    │ │ │ Batch Processing│
            │ (Port 8004)     │ │ │  (Port 8005)    │
            └─────────────────┘ │ └─────────────────┘
                       │        │        │
            ┌─────────────────┐ │ ┌─────────────────┐
            │  Monitoring     │ │ │ Ingest Service  │
            │  (Port 8006)    │ │ │  (Port 9001)    │
            └─────────────────┘   └─────────────────┘
```

## 🚀 Services Overview

### 1. API Gateway (Port 8000)
- **Purpose**: Central entry point for all API requests
- **Features**:
  - Request routing and load balancing
  - API key authentication
  - Rate limiting
  - Request/response logging
  - Service health monitoring

### 2. Model Service (Port 8001)
- **Purpose**: Core fraud detection ML model
- **Features**:
  - Real-time transaction scoring
  - Model versioning
  - Prediction confidence scoring
  - Model performance metrics

### 3. Analytics Service (Port 8002)
- **Purpose**: Advanced analytics and reporting
- **Features**:
  - Fraud trend analysis
  - Transaction pattern detection
  - Risk distribution analysis
  - Dashboard data aggregation

### 4. Database Service (Port 8003)
- **Purpose**: Persistent data storage
- **Features**:
  - Transaction storage
  - Prediction history
  - System logs
  - Performance metrics

### 5. Notification Service (Port 8004)
- **Purpose**: Real-time alerts and notifications
- **Features**:
  - Email notifications
  - High-risk transaction alerts
  - System status alerts
  - Configurable alert thresholds

### 6. Batch Processing Service (Port 8005)
- **Purpose**: Bulk transaction processing
- **Features**:
  - CSV file processing
  - Bulk scoring operations
  - Job queue management
  - Progress tracking

### 7. Monitoring Service (Port 8006)
- **Purpose**: System health and performance monitoring
- **Features**:
  - Service health checks
  - System resource monitoring
  - Alert generation
  - Performance metrics

### 8. Ingest Service (Port 9001)
- **Purpose**: Transaction ingestion and preprocessing
- **Features**:
  - Data validation
  - Transaction storage
  - Model service integration
  - Data quality checks

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fraud-detection-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Create the ML model**
   ```bash
   python create_model.py
   ```

5. **Start all services**
   ```bash
   python start_services.py
   ```

6. **Start the frontend**
   ```bash
   python start_frontend.py
   ```

### Manual Service Startup

You can also start services individually:

```bash
# Start API Gateway
python api_gateway.py

# Start Model Service
python model_service.py

# Start Analytics Service
python analytics_service.py

# Start Database Service
python database_service.py

# Start Notification Service
python notification_service.py

# Start Batch Processing Service
python batch_processing_service.py

# Start Monitoring Service
python monitoring_service.py

# Start Ingest Service
python ingest_service.py
```

## 📊 API Documentation

### API Gateway Endpoints

#### Authentication
All API requests require an API key in the header:
```
X-API-Key: your_api_key_here
```

#### Core Endpoints

**Health Check**
```
GET /health
```

**Service Status**
```
GET /services/status
```

**Transaction Scoring**
```
POST /api/v1/score
Content-Type: application/json

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
```

### Service-Specific Endpoints

#### Analytics Service
- `GET /fraud-trends?days=30` - Get fraud trends
- `GET /transaction-patterns` - Analyze transaction patterns
- `GET /risk-distribution` - Get risk score distribution
- `GET /model-performance` - Get model performance metrics

#### Database Service
- `POST /transactions` - Store transaction
- `GET /transactions` - Retrieve transactions
- `POST /predictions` - Store prediction
- `GET /predictions` - Retrieve predictions

#### Notification Service
- `POST /fraud-alert` - Send fraud alert
- `POST /system-alert` - Send system alert
- `GET /history` - Get notification history

#### Batch Processing Service
- `POST /jobs` - Create batch job
- `GET /jobs/{job_id}` - Get job status
- `GET /jobs` - List all jobs

#### Monitoring Service
- `GET /overview` - System overview
- `GET /services` - Service status
- `GET /metrics` - System metrics
- `GET /alerts` - System alerts

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=sqlite:///fraudshield.db

# Email Notifications
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# API Keys
FRONTEND_API_KEY=fs_frontend_key_123
ADMIN_API_KEY=fs_admin_key_456

# Monitoring Thresholds
ALERT_CPU_THRESHOLD=80
ALERT_MEMORY_THRESHOLD=85
ALERT_DISK_THRESHOLD=90

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### Service Configuration

Each service can be configured through:
- Environment variables
- Configuration files
- Command-line arguments

## 📈 Monitoring & Observability

### Health Checks
All services provide health check endpoints at `/health`

### Metrics
- System resource usage (CPU, memory, disk)
- Service response times
- Request rates and error rates
- Model performance metrics

### Alerts
- High-risk transaction alerts
- Service downtime alerts
- Resource usage alerts
- Performance degradation alerts

### Logging
Structured logging with configurable levels:
- INFO: General operational messages
- WARNING: Potential issues
- ERROR: Error conditions
- DEBUG: Detailed debugging information

## 🔒 Security

### Authentication
- API key-based authentication
- Rate limiting per client
- Request validation

### Data Protection
- Input sanitization
- SQL injection prevention
- Secure data storage

### Network Security
- CORS configuration
- HTTPS support (in production)
- Service-to-service authentication

## 🧪 Testing

### Unit Tests
```bash
python -m pytest tests/unit/
```

### Integration Tests
```bash
python -m pytest tests/integration/
```

### Load Testing
```bash
python -m pytest tests/load/
```

## 📦 Deployment

### Docker Deployment
```bash
docker-compose up -d
```

### Production Considerations
- Use production-grade databases (PostgreSQL, MySQL)
- Implement proper logging aggregation
- Set up monitoring and alerting
- Configure load balancers
- Implement backup strategies

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the documentation
- Review the logs
- Contact the development team

## 🔄 Version History

- **v1.0.0**: Initial release with core services
- **v1.1.0**: Added analytics and monitoring
- **v1.2.0**: Enhanced batch processing
- **v1.3.0**: Improved notifications and alerts
