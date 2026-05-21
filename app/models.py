import joblib
import pandas as pd
from pathlib import Path

# Paths to the trained model and encoders
MODEL_PATH = Path(__file__).parent.parent / "model" / "rf_demand.pkl"
ENCODERS_PATH = Path(__file__).parent.parent / "model" / "encoders.pkl"

# Global variables
model = None
encoders = None

def load_model():
    """Load or reload the model and encoders from disk."""
    global model, encoders
    if MODEL_PATH.exists():
        model = joblib.load(MODEL_PATH)
    if ENCODERS_PATH.exists():
        encoders = joblib.load(ENCODERS_PATH)
    return model, encoders

# Initial load
load_model()

def safe_encode(encoder, value):
    """Encode a categorical value using the provided encoder.
    If the value is not present, try fallback values, then use first class.
    """
    if value in encoder.classes_:
        return encoder.transform([value])[0]
    # Fallback values that were used during training
    defaults = ['desconocida', 'no especificado', 'sin categoría', 'boleta', 'efectivo', 'nan']
    for d in defaults:
        if d in encoder.classes_:
            return encoder.transform([d])[0]
    # Last resort: use the first class
    return encoder.transform([encoder.classes_[0]])[0]

def preprocess(payload: dict) -> pd.DataFrame:
    """Convert incoming JSON payload to a DataFrame matching the model's expected schema.
    
    The improved model expects these 14 features in order:
    Base features (6):
    1-6. producto, tipo_producto, marca, categoria, metodo_pago, comprobante (categorical, encoded)
    
    Numeric features (8):
    7. precio_unitario
    8. mes (1-12)
    9. trimestre (1-4)
    10. dia_semana (0-6)
    11. es_fin_semana (0 or 1)
    12. producto_popularidad
    13. producto_demanda_promedio
    14. precio_relativo
    """
    # Create DataFrame from payload
    df = pd.DataFrame([payload])
    
    # Ensure precio_unitario is numeric
    df["precio_unitario"] = pd.to_numeric(df["precio_unitario"], errors="coerce").fillna(0)
    
    # Add temporal features (use current date if not provided)
    from datetime import datetime
    current_date = datetime.now()
    df['mes'] = current_date.month
    df['trimestre'] = (current_date.month - 1) // 3 + 1
    df['dia_semana'] = current_date.weekday()
    df['es_fin_semana'] = 1 if current_date.weekday() >= 5 else 0
    
    # Load dataset for statistical features

    # Load dataset for statistical features
    df_opts = _load_data()

    
    # Add statistical features
    producto = payload.get('producto', 'Desconocido')
    categoria = payload.get('categoria', 'Sin categoría')
    
    # Product popularity
    product_counts = df_opts.groupby('producto').size()
    df['producto_popularidad'] = product_counts.get(producto, 1)
    
    # Average demand per product
    product_avg_demand = df_opts.groupby('producto')['cantidad'].mean()
    df['producto_demanda_promedio'] = product_avg_demand.get(producto, 100.0)
    if pd.isna(df['producto_demanda_promedio'].iloc[0]):
        df['producto_demanda_promedio'] = 100.0
    
    # Average price per category
    category_avg_price = df_opts.groupby('categoria')['precio_unitario'].mean()
    categoria_precio_promedio = category_avg_price.get(categoria, df['precio_unitario'].iloc[0])
    if pd.isna(categoria_precio_promedio) or categoria_precio_promedio == 0:
        categoria_precio_promedio = df['precio_unitario'].iloc[0]
    
    # Price relative to category average
    if categoria_precio_promedio > 0:
        df['precio_relativo'] = df['precio_unitario'] / categoria_precio_promedio
    else:
        df['precio_relativo'] = 1.0
    
    # Encode categorical columns (normalize text first - lowercase and strip)
    for col, encoder in encoders.items():
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
            df[col] = df[col].apply(lambda x: safe_encode(encoder, x))
    
    # Return features in the exact order the model expects
    feature_order = [
        "producto",
        "tipo_producto",
        "marca",
        "categoria",
        "metodo_pago",
        "comprobante",
        "precio_unitario",
        "mes",
        "trimestre",
        "dia_semana",
        "es_fin_semana",
        "producto_popularidad",
        "producto_demanda_promedio",
        "precio_relativo"
    ]
    
    return df[feature_order]


# Path to the dataset used for dropdown options
DATA_PATH = Path(__file__).parent.parent / "ferreteria_COSTOS_ventas_2024.csv"
_df_options = None

def _load_data():
    """Helper to load and preprocess the options dataframe."""
    global _df_options
    if _df_options is None:
        if not DATA_PATH.exists():
            # Return empty DF with expected columns if file missing
            _df_options = pd.DataFrame(columns=['producto', 'tipo_producto', 'marca', 'categoria', 'cantidad', 'precio_unitario', 'metodo_pago'])
        else:
            _df_options = pd.read_csv(DATA_PATH)
            
        # Apply fill strategy
        _df_options['marca'] = _df_options['marca'].fillna('Desconocida')
        _df_options['tipo_producto'] = _df_options['tipo_producto'].fillna('No especificado')
        _df_options['categoria'] = _df_options['categoria'].fillna('Sin categoría')
        
        # Ensure numeric columns are actually numeric
        # coerce errors will turn non-numeric strings to NaN
        if 'cantidad' in _df_options.columns:
            _df_options['cantidad'] = pd.to_numeric(_df_options['cantidad'], errors='coerce').fillna(0)
        if 'precio_unitario' in _df_options.columns:
            _df_options['precio_unitario'] = pd.to_numeric(_df_options['precio_unitario'], errors='coerce').fillna(0)
            
    return _df_options

def get_options():
    """Return unique values for dropdowns and mappings for dependent selects."""
    df = _load_data()
    
    # Build product -> marcas / categorias mappings
    product_mappings = {}
    if 'producto' in df.columns:
        unique_products = sorted(df['producto'].astype(str).unique().tolist())
    else:
        unique_products = []
    
    for prod in unique_products:
        subset = df[df['producto'] == prod]
        categorias_prod = sorted(subset['categoria'].astype(str).unique().tolist())
        categorias_prod = [c for c in categorias_prod if c.lower() not in ['sin categoría', 'sin categoria']]
        # Calculate average price
        avg_price = 10.0
        if 'precio_unitario' in subset.columns and not subset.empty:
            avg_price = float(subset['precio_unitario'].mean())
            if pd.isna(avg_price):
                avg_price = 10.0
        
        product_mappings[prod] = {
            "marcas": sorted(subset['marca'].astype(str).unique().tolist()),
            "categorias": categorias_prod,
            "avg_price": avg_price
        }
    
    # Filter out unwanted values
    categorias = []
    if 'categoria' in df.columns:
        categorias = sorted(df['categoria'].astype(str).unique().tolist())
        categorias = [c for c in categorias if c.lower() not in ['sin categoría', 'sin categoria']]
    
    # Calculate average prices by category
    category_prices = {}
    for cat in categorias:
        subset = df[df['categoria'] == cat]
        avg_price = 10.0
        if 'precio_unitario' in subset.columns and not subset.empty:
            avg_price = float(subset['precio_unitario'].mean())
            if pd.isna(avg_price):
                avg_price = 10.0
        category_prices[cat] = avg_price
    
    return {
        "producto": unique_products,
        "tipo_producto": sorted(df['tipo_producto'].astype(str).unique().tolist()) if 'tipo_producto' in df.columns else [],
        "marca": sorted(df['marca'].astype(str).unique().tolist()) if 'marca' in df.columns else [],
        "categoria": categorias,
        "metodo_pago": sorted(df['metodo_pago'].dropna().unique().tolist()) if "metodo_pago" in df.columns else ["efectivo", "tarjeta", "transferencia"],
        "mappings": product_mappings,
        "category_prices": category_prices,
    }

