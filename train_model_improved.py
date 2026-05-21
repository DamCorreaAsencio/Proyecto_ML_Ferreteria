"""
Enhanced training script with feature engineering and hyperparameter optimization.
Improves model accuracy while maintaining backward compatibility.
"""
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import r2_score, mean_absolute_error
import warnings
import json

warnings.filterwarnings('ignore')

# Paths
DATA_PATH = Path(__file__).parent / "ferreteria_COSTOS_ventas_2025.csv"
MODEL_PATH = Path(__file__).parent / "model" / "rf_demand.pkl"
ENCODERS_PATH = Path(__file__).parent / "model" / "encoders.pkl"
METRICS_PATH = Path(__file__).parent / "model" / "metrics.json"

def train():
    print("=" * 60)
    print("ENHANCED MODEL TRAINING - DEMAND PREDICTION")
    print("=" * 60)

    # Load data
    print("\n[1/7] Loading data...")
    if not DATA_PATH.exists():
        return {"error": "Data file not found"}
        
    df = pd.read_csv(DATA_PATH)
    print(f"   Loaded {len(df)} records")

    # Data cleaning
    print("\n[2/7] Cleaning data...")
    # Convert numeric columns
    df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce')
    df['precio_unitario'] = pd.to_numeric(df['precio_unitario'], errors='coerce')

    # Drop rows with missing target or price
    initial_size = len(df)
    df = df.dropna(subset=['cantidad', 'precio_unitario'])
    print(f"   Removed {initial_size - len(df)} rows with missing values")

    # Fill missing categorical values
    df['marca'] = df['marca'].fillna('Desconocida')
    df['tipo_producto'] = df['tipo_producto'].fillna('No especificado')
    df['categoria'] = df['categoria'].fillna('Sin categoría')
    df['producto'] = df['producto'].fillna('Desconocido')

    # Convert fecha to datetime
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df = df.dropna(subset=['fecha'])
    print(f"   Final dataset size: {len(df)} records")

    # Feature Engineering
    print("\n[3/7] Engineering features...")

    # Temporal features
    df['mes'] = df['fecha'].dt.month
    df['trimestre'] = df['fecha'].dt.quarter
    df['dia_semana'] = df['fecha'].dt.dayofweek
    df['es_fin_semana'] = (df['dia_semana'] >= 5).astype(int)

    # Statistical features - product popularity
    product_counts = df.groupby('producto').size()
    df['producto_popularidad'] = df['producto'].map(product_counts)

    # Average demand per product
    product_avg_demand = df.groupby('producto')['cantidad'].mean()
    df['producto_demanda_promedio'] = df['producto'].map(product_avg_demand)

    # Average price per category
    category_avg_price = df.groupby('categoria')['precio_unitario'].mean()
    df['categoria_precio_promedio'] = df['categoria'].map(category_avg_price)

    # Price relative to category average
    df['precio_relativo'] = df['precio_unitario'] / df['categoria_precio_promedio']
    df['precio_relativo'] = df['precio_relativo'].fillna(1.0)

    print(f"   Added 8 engineered features")

    # Prepare features
    base_features = ['producto', 'tipo_producto', 'marca', 'categoria', 'metodo_pago', 'comprobante']
    numeric_features = ['precio_unitario', 'mes', 'trimestre', 'dia_semana', 'es_fin_semana', 
                       'producto_popularidad', 'producto_demanda_promedio', 'precio_relativo']
    all_features = base_features + numeric_features
    target = 'cantidad'

    # Encode categorical features
    print("\n[4/7] Encoding categorical features...")
    encoders = {}
    for col in base_features:
        le = LabelEncoder()
        df[col] = df[col].astype(str).str.strip().str.lower()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le

    # Save encoders (for compatibility with existing backend)
    joblib.dump(encoders, ENCODERS_PATH)
    print(f"   Encoded {len(base_features)} categorical features")

    # Prepare X and y
    X = df[all_features]
    y = df[target]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"   Train size: {len(X_train)}, Test size: {len(X_test)}")

    # Train models
    print("\n[5/7] Training models...")

    # Try XGBoost first (usually better for tabular data)
    best_model = None
    best_r2 = 0
    best_mae = float('inf')
    best_name = None

    try:
        from xgboost import XGBRegressor
        print("   Testing XGBoost...")
        
        xgb_model = XGBRegressor(
            n_estimators=200,
            max_depth=10,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        xgb_model.fit(X_train, y_train)
        xgb_pred = xgb_model.predict(X_test)
        xgb_r2 = r2_score(y_test, xgb_pred)
        xgb_mae = mean_absolute_error(y_test, xgb_pred)
        print(f"   XGBoost R²: {xgb_r2:.4f}, MAE: {xgb_mae:.2f}")
        
        best_model = xgb_model
        best_r2 = xgb_r2
        best_mae = xgb_mae
        best_name = "XGBoost"
        
    except ImportError:
        print("   XGBoost not available, using Random Forest")

    # Train optimized Random Forest
    print("   Training optimized Random Forest...")
    rf_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    rf_pred = rf_model.predict(X_test)
    rf_r2 = r2_score(y_test, rf_pred)
    rf_mae = mean_absolute_error(y_test, rf_pred)
    print(f"   Random Forest R²: {rf_r2:.4f}, MAE: {rf_mae:.2f}")

    # Select best model
    if rf_r2 > best_r2:
        best_model = rf_model
        best_r2 = rf_r2
        best_mae = rf_mae
        best_name = "Random Forest"

    print(f"\n   Best model: {best_name}")
    print(f"   R² Score: {best_r2:.4f} ({best_r2*100:.2f}%)")
    print(f"   MAE: {best_mae:.2f}")

    # Calculate metrics
    print("\n[6/7] Calculating final metrics...")
    mean_y = y_test.mean()
    error_pct = (best_mae / mean_y) * 100 if mean_y > 0 else 0

    print(f"   Accuracy: {best_r2*100:.2f}%")
    print(f"   Error percentage: {error_pct:.2f}%")

    # Save model
    print("\n[7/7] Saving model...")
    joblib.dump(best_model, MODEL_PATH)
    print(f"   Model saved to {MODEL_PATH}")

    # Save metrics
    metrics = {
        "r2_score": round(best_r2, 4),
        "accuracy_pct": round(best_r2 * 100, 2),
        "mae": round(best_mae, 2),
        "error_pct": round(error_pct, 2),
        "model_type": best_name
    }

    with open(METRICS_PATH, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"   Metrics saved to {METRICS_PATH}")

    print("\n✅ Training complete! Model is ready for use.")
    return metrics

if __name__ == "__main__":
    train()
