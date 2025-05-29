#!/usr/bin/env python3
"""
Create a simple fraud detection model for testing purposes.
This creates a basic RandomForestClassifier that can be used by the services.
"""

import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

def create_sample_data():
    """Create sample fraud detection data for training."""
    np.random.seed(42)
    
    # Create synthetic data similar to the fraud dataset
    n_samples = 10000
    
    data = {
        'step': np.random.randint(1, 100, n_samples),
        'amount': np.random.exponential(1000, n_samples),
        'oldbalanceOrg': np.random.exponential(5000, n_samples),
        'newbalanceOrig': np.random.exponential(4000, n_samples),
        'oldbalanceDest': np.random.exponential(3000, n_samples),
        'newbalanceDest': np.random.exponential(3500, n_samples),
        'type_CASH_OUT': np.random.binomial(1, 0.2, n_samples),
        'type_DEBIT': np.random.binomial(1, 0.1, n_samples),
        'type_PAYMENT': np.random.binomial(1, 0.5, n_samples),
        'type_TRANSFER': np.random.binomial(1, 0.2, n_samples),
        'merchantFlag': np.random.binomial(1, 0.3, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Create fraud labels based on some simple rules
    fraud_conditions = (
        (df['amount'] > 10000) & 
        (df['type_CASH_OUT'] == 1) & 
        (df['oldbalanceOrg'] > df['newbalanceOrig'] + df['amount'] * 0.9)
    ) | (
        (df['amount'] > 5000) & 
        (df['type_TRANSFER'] == 1) & 
        (df['oldbalanceDest'] == 0)
    )
    
    df['isFraud'] = fraud_conditions.astype(int)
    
    # Add some random fraud cases to increase fraud rate
    additional_fraud = np.random.choice(
        df[df['isFraud'] == 0].index, 
        size=int(0.01 * len(df)), 
        replace=False
    )
    df.loc[additional_fraud, 'isFraud'] = 1
    
    return df

def train_model():
    """Train a RandomForest model on the sample data."""
    print("Creating sample data...")
    df = create_sample_data()
    
    # Define features
    feature_columns = [
        'step', 'amount', 'oldbalanceOrg', 'newbalanceOrig',
        'oldbalanceDest', 'newbalanceDest', 'type_CASH_OUT',
        'type_DEBIT', 'type_PAYMENT', 'type_TRANSFER', 'merchantFlag'
    ]
    
    X = df[feature_columns]
    y = df['isFraud']
    
    print(f"Dataset shape: {X.shape}")
    print(f"Fraud rate: {y.mean():.3f}")
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train the model
    print("Training RandomForest model...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate the model
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    print(f"Training accuracy: {train_score:.3f}")
    print(f"Testing accuracy: {test_score:.3f}")
    
    # Save the model with feature columns
    model_data = {
        'model': model,
        'feature_columns': feature_columns
    }
    
    print("Saving model to fraud_detection_model.pkl...")
    with open('fraud_detection_model.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    
    print("Model saved successfully!")
    
    # Test the saved model
    print("\nTesting saved model...")
    with open('fraud_detection_model.pkl', 'rb') as f:
        loaded_data = pickle.load(f)
    
    loaded_model = loaded_data['model']
    loaded_features = loaded_data['feature_columns']
    
    print(f"Loaded model type: {type(loaded_model)}")
    print(f"Feature columns: {loaded_features}")
    print(f"Model has predict_proba: {hasattr(loaded_model, 'predict_proba')}")
    
    # Test prediction
    sample_prediction = loaded_model.predict_proba(X_test[:1])
    print(f"Sample prediction: {sample_prediction}")
    
    return model_data

if __name__ == '__main__':
    train_model()
