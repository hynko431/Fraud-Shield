# FraudShield Frontend

A modern, responsive web interface for the FraudShield fraud detection system.

## Features

- **Real-time Fraud Detection**: Submit transactions and get instant fraud risk scores
- **Service Status Monitoring**: Live monitoring of backend services health
- **Transaction History**: View and replay recent test transactions
- **Dark Mode Support**: Toggle between light and dark themes
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Enhanced UX**: Smooth animations, notifications, and intuitive interface

## Files Overview

### Core Files
- `ap.html` - Main application interface
- `styles.css` - Custom CSS styles and animations
- `config.js` - Configuration settings and utilities

### Backend Services (Required)
- `model_service.py` - ML model service (port 8001)
- `ingest_service.py` - Data ingestion service (port 9001)

## Quick Start

1. **Start Backend Services**:
   ```bash
   # Start both services
   python start_services.py
   
   # Or start individually
   python model_service.py    # Port 8001
   python ingest_service.py   # Port 9001
   ```

2. **Open Frontend**:
   - Simply open `ap.html` in your web browser
   - Or serve it using a local web server:
     ```bash
     # Using Python
     python -m http.server 8080
     
     # Using Node.js
     npx serve .
     ```

3. **Test the System**:
   - Check service status indicators (should show green)
   - Fill out the transaction form
   - Click "Check for Fraud" to analyze transactions
   - View results and transaction history

## Configuration

Edit `config.js` to customize:

- **Service URLs**: Change backend service endpoints
- **UI Settings**: Modify timeouts, animations, theme preferences
- **Validation Rules**: Adjust transaction validation patterns
- **Risk Thresholds**: Configure risk level boundaries

Example configuration change:
```javascript
// Change service URLs for production
services: {
    modelService: 'https://api.yourcompany.com/model',
    ingestService: 'https://api.yourcompany.com/ingest'
}
```

## Customization

### Styling
- Modify `styles.css` for custom themes and animations
- Uses Tailwind CSS for utility classes
- Supports dark mode with automatic theme switching

### Features
- Enable/disable features in `config.js`:
  ```javascript
  features: {
      darkMode: true,
      exportData: true,
      transactionHistory: true,
      notifications: true
  }
  ```

### Risk Levels
- Customize risk thresholds and colors:
  ```javascript
  risk: {
      low: 0.3,      // 0-30% = Low risk
      medium: 0.7,   // 30-70% = Medium risk
      // 70-100% = High risk
  }
  ```

## Browser Support

- **Modern Browsers**: Chrome 80+, Firefox 75+, Safari 13+, Edge 80+
- **Features Used**: ES6+, Fetch API, CSS Grid, CSS Custom Properties
- **Fallbacks**: Graceful degradation for older browsers

## Security Considerations

- **CORS**: Backend services have CORS enabled for frontend communication
- **Input Validation**: Client-side validation with server-side verification
- **No Sensitive Data**: No authentication tokens or sensitive data stored locally

## Troubleshooting

### Service Connection Issues
1. Check if backend services are running:
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:9001/health
   ```

2. Verify CORS settings in backend services
3. Check browser console for error messages

### Common Issues
- **Services Offline**: Red status indicators - start backend services
- **CORS Errors**: Ensure backend services have CORS enabled
- **Validation Errors**: Check transaction data format requirements

### Browser Console
Enable browser developer tools to see detailed error messages and network requests.

## Development

### Adding New Features
1. Update `config.js` for new settings
2. Add feature flag in `config.features`
3. Implement UI changes in `ap.html`
4. Add styling in `styles.css`

### Testing
- Test with different transaction types and amounts
- Verify service fallback behavior (stop one service)
- Test responsive design on mobile devices
- Validate dark mode functionality

## Performance

- **Lightweight**: Minimal dependencies (Tailwind CSS, Font Awesome)
- **Fast Loading**: Optimized CSS and JavaScript
- **Efficient**: Local storage for history, minimal API calls
- **Responsive**: Smooth animations and transitions

## License

This frontend is part of the FraudShield fraud detection system.
