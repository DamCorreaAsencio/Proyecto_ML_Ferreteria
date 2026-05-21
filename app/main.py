import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from .router import router

from pathlib import Path

app = FastAPI(
    title="Predicción de demanda – Ferretería",
    description="API para estimar la demanda de cualquier producto usando un modelo entrenado.",
    version="0.1.0",
)

# Montar carpeta estática (HTML)
static_dir = Path(__file__).parent.parent / "static"

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

# Incluir router con endpoint /predict
app.include_router(router)

# Mount static files last
app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    # Ejecutar con: python -m uvicorn app.main:app --reload
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
