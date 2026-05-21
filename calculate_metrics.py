"""
Simplified script to calculate and save model performance metrics.
"""
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import r2_score, mean_absolute_error

# Paths
MODEL_PATH = Path("model/rf_demand.pkl")
ENCODERS_PATH = Path("model/encoders.pkl")
DATA_PATH = Path("ferreteria_COSTOS_ventas_2024.csv")
METRICS_PATH = Path("model/metrics.json")

# Load model and encoders
model = joblib.load(MODEL_PATH)
encoders = joblib.load(ENCODERS_PATH)

# Load data
df = pd.read_csv(DATA_PATH)

# Apply same preprocessing as training
df['marca'] = df['marca'].fillna('Desconocida')
df['tipo_producto'] = df['tipo_producto'].fillna('No especificado')
df['categoria'] = df['categoria'].fillna('Sin categoría')

# Prepare features - MUST match exact order from training
feature_cols = ['producto', 'tipo_producto', 'marca', 'categoria', 'metodo_pago', 'comprobante']
target_col = 'cantidad'

# Convert cantidad to numeric, handling errors
df[target_col] = pd.to_numeric(df[target_col], errors='coerce')

# Drop rows with missing target
df = df.dropna(subset=[target_col])

# Convert precio_unitario to numeric, handling errors
df['precio_unitario'] = pd.to_numeric(df['precio_unitario'], errors='coerce')
df = df.dropna(subset=['precio_unitario'])  # Drop rows with invalid prices

# Add temporal features
df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
df = df.dropna(subset=['fecha'])
df['mes'] = df['fecha'].dt.month
df['trimestre'] = df['fecha'].dt.quarter
df['dia_semana'] = df['fecha'].dt.dayofweek
df['es_fin_semana'] = (df['dia_semana'] >= 5).astype(int)

# Add statistical features
product_counts = df.groupby('producto').size()
df['producto_popularidad'] = df['producto'].map(product_counts)

product_avg_demand = df.groupby('producto')['cantidad'].mean()
df['producto_demanda_promedio'] = df['producto'].map(product_avg_demand)

category_avg_price = df.groupby('categoria')['precio_unitario'].mean()
df['categoria_precio_promedio'] = df['categoria'].map(category_avg_price)

df['precio_relativo'] = df['precio_unitario'] / df['categoria_precio_promedio']
df['precio_relativo'] = df['precio_relativo'].fillna(1.0)

# Encode categorical features using safe encoding
def safe_encode(encoder, value):
    if value in encoder.classes_:
        return encoder.transform([value])[0]
    # Use first class as fallback
    return encoder.transform([encoder.classes_[0]])[0]

for col, encoder in encoders.items():
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.lower()
        df[col] = df[col].apply(lambda x: safe_encode(encoder, x))

# Prepare X and y with correct feature order
# Base features: producto, tipo_producto, marca, categoria, metodo_pago, comprobante
# Numeric features: precio_unitario, mes, trimestre, dia_semana, es_fin_semana, 
#                   producto_popularidad, producto_demanda_promedio, precio_relativo
all_features = feature_cols + ['precio_unitario', 'mes', 'trimestre', 'dia_semana', 'es_fin_semana', 
                               'producto_popularidad', 'producto_demanda_promedio', 'precio_relativo']
X = df[all_features]
y = df[target_col]

print(f"Dataset size: {len(X)} samples")

# Make predictions on full dataset (as a proxy for performance)
y_pred = model.predict(X)

# Calculate metrics
r2 = r2_score(y, y_pred)
mae = mean_absolute_error(y, y_pred)

# Calculate accuracy as percentage (R² * 100)
accuracy = r2 * 100

# Calculate error percentage relative to mean
mean_y = y.mean()
error_pct = (mae / mean_y) * 100 if mean_y > 0 else 0

print(f"\nModel Performance Metrics:")
print(f"R² Score: {r2:.4f} ({accuracy:.2f}%)")
print(f"Mean Absolute Error: {mae:.2f}")
print(f"Error Percentage: {error_pct:.2f}%")

# Save metrics to JSON
import json
metrics = {
    "r2_score": round(r2, 4),
    "accuracy_pct": round(accuracy, 2),
    "mae": round(mae, 2),
    "error_pct": round(error_pct, 2)
}

with open(METRICS_PATH, 'w') as f:
    json.dump(metrics, f, indent=2)

print(f"\nMetrics saved to {METRICS_PATH}")
