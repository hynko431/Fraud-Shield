# FraudShield Frontend-Backend Integration Guide

This guide explains how the FraudShield frontend and backend components are integrated and how to run the complete system.

## 🏗️ Integration Architecture

The FraudShield system now features a fully integrated architecture with multiple deployment options:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │  Backend        │
│   (Port 8080)   │◄──►│   (Port 8000)   │◄──►│  Services       │
│                 │    │   [Optional]    │    │  (Various Ports)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         └──────────────────────────────────────────────┘
                    Direct Connection (Fallback)
```

## 🚀 Quick Start Options

### Option 1: Basic Setup (Recommended for Testing)
Start only the essential services for basic fraud detection:

```bash
python start_basic.py
```

This starts:
- Model Service (Port 8001)
- Ingest Service (Port 9001)
- Frontend Server (Port 3000)

### Option 2: Full Integration (Complete System)
Start all services with API Gateway:

```bash
python integrated_startup.py
```

This starts all services:
- API Gateway (Port 8000)
- Model Service (Port 8001)
- Analytics Service (Port 8002)
- Database Service (Port 8003)
- Notification Service (Port 8004)
- Batch Processing Service (Port 8005)
- Monitoring Service (Port 8006)
- Ingest Service (Port 9001)
- Frontend Server (Port 3000)

### Option 3: Manual Service Management
Start services individually using the original script:

```bash
python start_services.py
```

## 🔧 Configuration Options

### Frontend Configuration (`config.js`)

The frontend can operate in two modes:

#### Direct Service Mode (Default)
```javascript
api: {
    useGateway: false,  // Direct service communication
    gatewayUrl: 'http://localhost:8000'
}
```

#### API Gateway Mode
```javascript
api: {
    useGateway: true,   // Route through API Gateway
    gatewayUrl: 'http://localhost:8000'
}
```

## 🔄 Integration Features

### 1. Intelligent Service Discovery
- Frontend automatically detects available services
- Graceful fallback from API Gateway to direct services
- Real-time service health monitoring

### 2. Enhanced Error Handling
- Multiple retry mechanisms
- Detailed error reporting
- Service-specific error messages

### 3. Flexible Deployment
- Can run with minimal services (Model + Ingest)
- Supports full microservices architecture
- Easy scaling and service addition

### 4. Unified Authentication
- API key-based authentication when using Gateway
- Consistent security across all services

## 📊 Service Dependencies

```
API Gateway
├── Model Service (Core)
├── Ingest Service → Model Service
├── Analytics Service → Database Service
├── Database Service (Core)
├── Notification Service (Independent)
├── Batch Processing → Model Service
└── Monitoring Service (Independent)
```

## 🌐 Access Points

After starting services, access the application at:

- **Web Application**: http://localhost:8080/ap.html
- **API Gateway**: http://localhost:8000 (if enabled)
- **Model Service**: http://localhost:8001
- **Analytics Service**: http://localhost:8002
- **Database Service**: http://localhost:8003
- **Notification Service**: http://localhost:8004
- **Batch Processing**: http://localhost:8005
- **Monitoring Service**: http://localhost:8006
- **Ingest Service**: http://localhost:9001

## 🔍 Health Monitoring

### Service Status Check
The frontend automatically checks service health and displays status indicators:
- ✅ Green: Service online and healthy
- ⚠️ Yellow: Service degraded or using fallback
- ❌ Red: Service offline

### Manual Health Checks
Check individual service health:
```bash
curl http://localhost:8001/health  # Model Service
curl http://localhost:9001/health  # Ingest Service
curl http://localhost:8000/health  # API Gateway
```

## 🛠️ Troubleshooting

### Common Issues

1. **Port Already in Use**
   - Check if services are already running
   - Use different ports if needed
   - Kill existing processes: `pkill -f "python.*service"`

2. **Model File Missing**
   - Ensure `fraud_detection_model.pkl` exists
   - Run model training if needed: `python create_model.py`

3. **Frontend Can't Connect**
   - Check service health endpoints
   - Verify CORS is enabled
   - Check browser console for errors

4. **API Gateway Issues**
   - Verify API key configuration
   - Check service URLs in gateway config
   - Try direct service mode as fallback

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export PYTHONPATH=.
export FLASK_ENV=development
python start_basic.py
```

## 🔒 Security Considerations

### API Gateway Mode
- All requests authenticated with API keys
- Rate limiting enabled
- Centralized request logging

### Direct Service Mode
- Services run on localhost only
- CORS enabled for frontend integration
- Input validation on all endpoints

## 📈 Performance Optimization

### For Development
- Use `start_basic.py` for faster startup
- Enable only required services
- Use direct service mode

### For Production
- Use `integrated_startup.py` with all services
- Enable API Gateway for better security
- Configure proper logging and monitoring

## 🔄 Switching Between Modes

### To Enable API Gateway:
1. Edit `config.js`: Set `useGateway: true`
2. Start with: `python integrated_startup.py`
3. Verify gateway health: `curl http://localhost:8000/health`

### To Use Direct Services:
1. Edit `config.js`: Set `useGateway: false`
2. Start with: `python start_basic.py`
3. Services communicate directly

## 📝 API Usage Examples

### Through API Gateway
```bash
curl -X POST http://localhost:8000/api/v1/score \
  -H "Content-Type: application/json" \
  -H "X-API-Key: fs_frontend_key_123" \
  -d '{"transactions": [...]}'
```

### Direct Service
```bash
curl -X POST http://localhost:8001/score \
  -H "Content-Type: application/json" \
  -d '{"transactions": [...]}'
```

## 🎯 Next Steps

1. **Start with Basic Setup**: Use `python start_basic.py` for initial testing
2. **Test Frontend**: Open http://localhost:8080/ap.html
3. **Verify Integration**: Submit test transactions and check results
4. **Scale Up**: Use `integrated_startup.py` for full feature set
5. **Customize**: Modify `config.js` for your specific needs

The integration is now complete and provides a robust, scalable fraud detection system with flexible deployment options!
