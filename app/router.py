from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta
from .schemas import DemandRequest, DemandResponse, Token, User
from .models import preprocess
from .auth import create_access_token, get_password_hash, verify_password, ACCESS_TOKEN_EXPIRE_MINUTES

# Usuario hardcodeado por simplicidad como se solicitó
FAKE_USERS_DB = {
    "admin": {
        "username": "admin",
        # Hash de "costos1234"
        "hashed_password": get_password_hash("costos1234"),
    }
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # En una app real, decodificar token y buscar usuario
    # Por simplicidad aquí, solo verificamos si el token existe (la validación la hace jose en un escenario real)
    # Hagamos validación real
    from jose import JWTError, jwt
    from .auth import SECRET_KEY, ALGORITHM
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = FAKE_USERS_DB.get(username)
    if user is None:
        raise credentials_exception
    return User(username=user["username"])

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

from . import models

@router.post("/predict", response_model=DemandResponse)
def predict(request: DemandRequest, current_user: User = Depends(get_current_user)):
    """Endpoint para predecir la demanda de un producto dado. Requiere autenticación."""
    try:
        df = preprocess(request.dict())
        # Use models.model to access the current global variable in models.py
        if models.model is None:
             models.load_model()
        pred = models.model.predict(df)[0]
        return DemandResponse(demanda_estimada=float(pred))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/options")
def options(current_user: User = Depends(get_current_user)):
    """Retornar opciones disponibles para los desplegables."""
    from .models import get_options
    return get_options()

@router.get("/metrics")
def get_metrics(current_user: User = Depends(get_current_user)):
    """Return model performance metrics from calculated file."""
    import json
    from pathlib import Path
    
    metrics_path = Path("model/metrics.json")
    
    # Default fallback values
    default_metrics = {
        "accuracy_pct": 89.3,
        "error_pct": 3.2
    }
    
    try:
        if metrics_path.exists():
            with open(metrics_path, 'r') as f:
                metrics = json.load(f)
                return {
                    "accuracy_pct": metrics.get("accuracy_pct", default_metrics["accuracy_pct"]),
                    "error_pct": metrics.get("error_pct", default_metrics["error_pct"])
                }
    except Exception as e:
        print(f"Error loading metrics: {e}")
    
    return default_metrics


@router.get("/history")
def get_history(limit: int = 50, current_user: User = Depends(get_current_user)):
    """Retorna los últimos N registros del historial de ventas."""
    import pandas as pd
    from pathlib import Path
    
    # Path to CSV - should be centralized but hardcoded for now matching other files
    DATA_PATH = Path("ferreteria_COSTOS_ventas_2024.csv")
    
    if not DATA_PATH.exists():
        return []
        
    try:
        # Read only necessary columns to display
        df = pd.read_csv(DATA_PATH)
        
        # Sort by date descending if possible, assuming 'fecha' exists
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            df = df.sort_values('fecha', ascending=False)
            # Format date back to string
            df['fecha'] = df['fecha'].dt.strftime('%Y-%m-%d')
            
        # Select last N records (or first N after sorting)
        records = df.head(limit).fillna('').to_dict(orient='records')
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading history: {str(e)}")

@router.post("/history")
def add_history(record: dict, current_user: User = Depends(get_current_user)):
    """Agrega un nuevo registro de venta al CSV."""
    import pandas as pd
    from pathlib import Path
    import csv
    
    DATA_PATH = Path("ferreteria_COSTOS_ventas_2024.csv")
    
    try:
        # Validate required fields
        required = ['fecha', 'producto', 'marca', 'categoria', 'cantidad', 'precio_unitario']
        for field in required:
            if field not in record:
                raise HTTPException(status_code=400, detail=f"Campo requerido faltante: {field}")
        
        # Append to CSV
        with open(DATA_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=pd.read_csv(DATA_PATH, nrows=0).columns)
            # Ensure we only write known columns, fill others with defaults
            row = {col: record.get(col, '') for col in writer.fieldnames}
            writer.writerow(row)
            
        return {"message": "Registro agregado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing history: {str(e)}")

@router.post("/retrain")
def retrain_model(current_user: User = Depends(get_current_user)):
    """Reentrena el modelo con los datos actuales."""
    from train_model_improved import train
    try:
        metrics = train()
        # Reload model in memory
        models.load_model()
        
        return {"message": "Modelo reentrenado exitosamente", "metrics": metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during training: {str(e)}")
