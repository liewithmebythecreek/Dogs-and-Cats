from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routes import api

app = FastAPI(
    title="Real-Time Weather Prediction API",
    description="FastAPI backend serving Open-Meteo data merged with LSTM predictions.",
    version="1.0.0"
)

# CORS — allow all origins in local dev (uvicorn is only bound to localhost)
# For production, replace "*" with the exact deployed frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # must be False when allow_origins="*"
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router)

@app.get("/")
def root():
    return {"message": "Welcome to Weather Prediction API. Go to /docs for Swagger UI."}
