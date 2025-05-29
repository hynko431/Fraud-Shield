/**
 * FraudShield Configuration
 * Centralized configuration for the fraud detection frontend
 */

window.FraudShieldConfig = {
    // Service URLs
    services: {
        apiGateway: 'http://localhost:8000',
        modelService: 'http://localhost:8001',
        ingestService: 'http://localhost:9001',
        analyticsService: 'http://localhost:8002',
        databaseService: 'http://localhost:8003',
        notificationService: 'http://localhost:8004',
        batchService: 'http://localhost:8005',
        monitoringService: 'http://localhost:8006'
    },

    // API endpoints
    endpoints: {
        health: '/health',
        score: '/api/v1/score',
        ingest: '/api/v1/ingest/ingest',
        transactions: '/api/v1/database/transactions',
        stats: '/api/v1/analytics/model-performance',
        export: '/api/v1/database/export',
        modelInfo: '/api/v1/model/model/info',
        serviceStatus: '/services/status',
        fraudTrends: '/api/v1/analytics/fraud-trends',
        riskDistribution: '/api/v1/analytics/risk-distribution',
        systemOverview: '/api/v1/monitoring/overview'
    },

    // API Configuration
    api: {
        key: 'fs_frontend_key_123',
        timeout: 30000,
        retries: 3,
        useGateway: false,  // Set to true to use API Gateway
        gatewayUrl: 'http://localhost:8000'
    },

    // UI Configuration
    ui: {
        // Maximum number of history items to display
        maxHistoryItems: 10,

        // Auto-refresh interval for service status (in milliseconds)
        statusRefreshInterval: 30000,

        // Request timeout (in milliseconds)
        requestTimeout: 10000,

        // Animation durations
        animations: {
            fadeIn: 300,
            slideUp: 300,
            notification: 3000
        },

        // Theme settings
        theme: {
            defaultMode: 'light', // 'light' or 'dark'
            persistPreference: true
        }
    },

    // Validation rules
    validation: {
        // Account number patterns
        accountPatterns: {
            origin: /^C\d{9}$/,
            destination: /^(M|C)\d{9}$/
        },

        // Transaction limits
        limits: {
            minAmount: 0.01,
            maxAmount: 1000000,
            minBalance: 0
        },

        // Valid transaction types
        transactionTypes: ['PAYMENT', 'TRANSFER', 'CASH_OUT', 'DEBIT']
    },

    // Risk thresholds
    risk: {
        low: 0.5,      // Below this is low risk
        medium: 0.8,   // Between low and this is medium risk
        // Above medium is high risk

        // Risk level colors
        colors: {
            low: {
                bg: 'bg-green-50',
                border: 'border-green-200',
                text: 'text-green-800',
                icon: 'text-green-600'
            },
            medium: {
                bg: 'bg-yellow-50',
                border: 'border-yellow-200',
                text: 'text-yellow-800',
                icon: 'text-yellow-600'
            },
            high: {
                bg: 'bg-red-50',
                border: 'border-red-200',
                text: 'text-red-800',
                icon: 'text-red-600'
            }
        }
    },

    // Local storage keys
    storage: {
        history: 'fraudDetectionHistory',
        darkMode: 'darkMode',
        userPreferences: 'userPreferences'
    },

    // Feature flags
    features: {
        darkMode: true,
        exportData: true,
        transactionHistory: true,
        serviceStatus: true,
        randomGenerator: true,
        notifications: true,
        autoSave: false
    },

    // Error messages
    messages: {
        errors: {
            networkError: 'Network connection failed. Please check your internet connection.',
            serviceUnavailable: 'Service is currently unavailable. Please try again later.',
            invalidData: 'Invalid transaction data. Please check your inputs.',
            timeout: 'Request timed out. Please try again.',
            unknown: 'An unexpected error occurred. Please contact support.'
        },

        success: {
            transactionScored: 'Transaction analyzed successfully',
            dataExported: 'Data exported successfully',
            settingsSaved: 'Settings saved successfully'
        },

        warnings: {
            serviceDown: 'Service is running in degraded mode',
            dataLoss: 'Some data may be lost if you continue'
        }
    },

    // Development settings
    development: {
        enableLogging: true,
        enableDebugMode: false,
        mockServices: false
    }
};

// Utility functions for configuration
window.FraudShieldConfig.utils = {
    /**
     * Get full URL for a service endpoint
     */
    getServiceUrl: function(service, endpoint) {
        const baseUrl = this.services[service];
        const endpointPath = this.endpoints[endpoint];
        return baseUrl + endpointPath;
    },

    /**
     * Get risk level based on score
     */
    getRiskLevel: function(score) {
        if (score < this.risk.low) return 'low';
        if (score < this.risk.medium) return 'medium';
        return 'high';
    },

    /**
     * Get risk colors for a given level
     */
    getRiskColors: function(level) {
        return this.risk.colors[level] || this.risk.colors.medium;
    },

    /**
     * Validate transaction data
     */
    validateTransaction: function(transaction) {
        const errors = [];

        // Check required fields
        const required = ['type', 'amount', 'nameOrig', 'nameDest', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest'];
        for (const field of required) {
            if (!(field in transaction) || transaction[field] === null || transaction[field] === undefined) {
                errors.push(`Missing required field: ${field}`);
            }
        }

        // Validate transaction type
        if (transaction.type && !this.validation.transactionTypes.includes(transaction.type)) {
            errors.push(`Invalid transaction type: ${transaction.type}`);
        }

        // Validate account numbers
        if (transaction.nameOrig && !this.validation.accountPatterns.origin.test(transaction.nameOrig)) {
            errors.push('Invalid origin account number format');
        }

        if (transaction.nameDest && !this.validation.accountPatterns.destination.test(transaction.nameDest)) {
            errors.push('Invalid destination account number format');
        }

        // Validate amounts
        if (transaction.amount !== undefined) {
            const amount = parseFloat(transaction.amount);
            if (isNaN(amount) || amount < this.validation.limits.minAmount || amount > this.validation.limits.maxAmount) {
                errors.push(`Amount must be between ${this.validation.limits.minAmount} and ${this.validation.limits.maxAmount}`);
            }
        }

        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }
};

// Make configuration available globally
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.FraudShieldConfig;
}
