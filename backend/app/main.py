from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.routes import api
from app.services.prometheus_drift import drift_monitor

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

@app.on_event("startup")
async def startup_event():
    await drift_monitor.start()


@app.on_event("shutdown")
async def shutdown_event():
    await drift_monitor.stop()


@app.get("/")
def root():
    return {"message": "Welcome to Weather Prediction API. Go to /docs for Swagger UI."}


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
