import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
import joblib
import os

# Create model directory if it doesn't exist
if not os.path.exists('model'):
    os.makedirs('model')

# Load data
print("Loading data...")
df = pd.read_csv('ferreteria_COSTOS_ventas_2024.csv')

# --- Preprocessing (Imputation) ---
print("Preprocessing data...")
# Convert dates and numeric columns to ensure correct types before filling
df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce')
df['precio_unitario'] = pd.to_numeric(df['precio_unitario'], errors='coerce')
df['precio_total'] = pd.to_numeric(df['precio_total'], errors='coerce')

# Impute missing values (Logic from notebook)
df['marca'] = df['marca'].fillna('Desconocida')
# Fix common misspellings as per previous fix
df['marca'] = df['marca'].replace({'desconcocida': 'Desconocida', 'desconocida': 'Desconocida'})
df['tipo_producto'] = df['tipo_producto'].fillna('No especificado')
df['categoria'] = df['categoria'].fillna('Sin categoría')

df['cantidad'] = df['cantidad'].fillna(df['cantidad'].median())
df['precio_unitario'] = df['precio_unitario'].fillna(df['precio_unitario'].median())
df['precio_total'] = df['precio_total'].fillna(df['precio_total'].median())

# Prepare for training
df_modelo = df.copy()
if 'fecha' in df_modelo.columns:
    df_modelo = df_modelo.sort_values('fecha').reset_index(drop=True)

# Encoding
label_cols = ['producto', 'tipo_producto', 'marca', 'categoria', 'metodo_pago']
# Note: 'comprobante' was in notebook but not in API schema. Including it if present in data, 
# but API might not send it. If API doesn't send it, model shouldn't rely on it or we need a default.
# The user's API schema didn't include 'comprobante'. 
# Let's check if 'comprobante' is important. The notebook used it. 
# If I train with it, I need it at inference.
# I will include it in training and update schemas.py later if needed, or just set a default in API.
if 'comprobante' in df.columns:
    label_cols.append('comprobante')

encoders = {}
print("Encoding categorical variables...")
for col in label_cols:
    le = LabelEncoder()
    # Ensure we fit on strings
    df_modelo[col] = le.fit_transform(df_modelo[col].astype(str))
    encoders[col] = le

# Save encoders
joblib.dump(encoders, 'model/encoders.pkl')
print("Encoders saved to model/encoders.pkl")

# Define features and target
TARGET = 'cantidad'
drop_cols = ['fecha', 'precio_total'] # precio_total is usually derived, and fecha isn't used directly in RF
# Also drop target
X = df_modelo.drop(columns=[TARGET] + [c for c in drop_cols if c in df_modelo.columns])
y = df_modelo[TARGET]

# Train model
print("Training RandomForestRegressor...")
model = RandomForestRegressor(
    n_estimators=200,
    random_state=42,
    n_jobs=-1,
    oob_score=True,
    max_features='sqrt',
    min_samples_split=5,
    min_samples_leaf=2
)
model.fit(X, y)

# Save model
joblib.dump(model, 'model/rf_demand.pkl')
print("Model saved to model/rf_demand.pkl")
print("Training complete.")
