from pydantic import BaseModel, Field
from typing import Literal, Optional

class DemandRequest(BaseModel):
    producto: str = Field(..., example="grava")
    tipo_producto: str = Field(..., example="NaN")
    marca: str = Field(..., example="Ladrillera Virú")
    categoria: str = Field(..., example="material_construccion")
    cantidad: Optional[float] = Field(None, example=5)  # Optional since not used by model
    precio_unitario: float = Field(..., example=36.86)
    metodo_pago: Literal["efectivo", "tarjeta", "transferencia"] = Field(..., example="efectivo")
    comprobante: str = Field("boleta", example="boleta")

class DemandResponse(BaseModel):
    demanda_estimada: float
    mensaje: str = "Predicción generada con éxito"

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
