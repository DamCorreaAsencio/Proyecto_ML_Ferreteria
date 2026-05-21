import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Configuración de rutas
CSV_PATH = "ferreteria_COSTOS_ventas_2025.csv"
OUTPUT_DIR = r"D:\Descargas\Proyecto_ML"

print("Cargando datos para evaluación de resultados...")
df = pd.read_csv(CSV_PATH, encoding='latin-1')

# Preprocesamiento rápido para simular el entrenamiento del PDF
df['fecha'] = pd.to_datetime(df['fecha'])
df = df.sort_values('fecha').reset_index(drop=True)
df['mes'] = df['fecha'].dt.month
df['dia_semana'] = df['fecha'].dt.dayofweek

features = ['mes', 'dia_semana']
X = df[features].fillna(0)
y = df['cantidad'].fillna(0)  # O 'precio_total' si predices ingresos

# División Temporal (Holdout: Último 15% para test según el PDF)
split_idx = int(len(df) * 0.85)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

print("Entrenando modelo evaluador...")
model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)

# Predicciones
y_pred = model.predict(X_test)

# Cálculo de Métricas Reales para tu informe texto
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
print(f"\nMétricas obtenidas:\n- MAE: {mae:.2f}\n- R2 Score: {r2:.2f}")

# ==========================================================
# GRÁFICO DE RESULTADOS 1: Predicción vs Valores Reales
# ==========================================================
print("Generando Gráfico: Predicciones vs Valores Reales...")
plt.figure(figsize=(10, 5))
# Tomamos una muestra de los últimos 100 datos para que se aprecie visualmente en el informe
plt.plot(y_test.values[-100:], label="Demanda Real (Histórico)", color="#1f77b4", linewidth=2, marker='o')
plt.plot(y_pred[-100:], label="Predicción del Modelo (Random Forest)", color="#ff7f0e", linestyle="--", linewidth=2, marker='x')

plt.title("Evaluación del Modelo: Predicción de Demanda vs Datos Reales", fontsize=12, fontweight='bold')
plt.xlabel("Muestra de Transacciones Recientes (Últimos registros)")
plt.ylabel("Cantidad de Productos / Unidades")
plt.legend(loc="upper right")
plt.tight_layout()

# Se guarda directo en tu carpeta
grafico_pred_path = os.path.join(OUTPUT_DIR, "resultado_predicciones_vs_real.png")
plt.savefig(grafico_pred_path, dpi=150)
plt.close()

# ==========================================================
# GRÁFICO DE RESULTADOS 2: Importancia de las Variables
# ==========================================================
print("Generando Gráfico: Importancia de Variables...")
importancias = model.feature_importances_
indices = np.argsort(importancias)

plt.figure(figsize=(8, 4))
plt.barh(range(len(indices)), importancias[indices], color="#2ca02c", align="center")
plt.yticks(range(len(indices)), [features[i] for i in indices])
plt.xlabel("Importancia Relativa")
plt.title("Importancia de las Variables en la Predicción de Demanda", fontsize=12, fontweight='bold')
plt.tight_layout()

grafico_imp_path = os.path.join(OUTPUT_DIR, "resultado_importancia_variables.png")
plt.savefig(grafico_imp_path, dpi=150)
plt.close()

print(f"\n¡Listo! Gráficos de resultados guardados en:\n1. {grafico_pred_path}\n2. {grafico_imp_path}")