# NeuralWeather: STGNN Weather Forecasting Platform

NeuralWeather is a full-stack weather forecasting system that combines:

- Live Open-Meteo data ingestion
- A spatio-temporal graph neural network (STGNN) for multi-city forecasting
- A React dashboard for interactive exploration
- Drift monitoring with Prometheus + scheduled MLOps fine-tuning

The current implementation forecasts **48 hours ahead** for a fixed **7-node city graph** in North India (Punjab region + nearby nodes).

## What Is Current In This Repo

- Model: **PyTorch STGNN** (`WeatherSTGNN`) with DenseGCN + LSTMCell + autoregressive decoder
- Input window: `48` historical hours
- Forecast horizon: `48` future hours
- Dynamic variables (6): temperature, humidity, wind speed, surface pressure, precipitation, weather code
- Graph nodes (7): Ropar, Chandigarh, Ludhiana, Patiala, Jalandhar, Ambala, Shimla
- Backend API routes: `/health`, `/current`, `/forecast`, `/metrics`, `/docs`
- Continuous drift checks exposed as Prometheus metrics

## Architecture

1. Backend (FastAPI)
- Fetches recent live history and native Open-Meteo forecast
- Runs STGNN inference when model artifacts are available
- Returns both Open-Meteo baseline and model forecast in one response
- Logs model predictions for drift evaluation

2. Model layer (PyTorch + PyG)
- Spatial message passing across the city graph
- Temporal dynamics with LSTMCell
- Autoregressive rollout for 48 steps

3. Frontend (React + Vite)
- ECMWF-inspired dashboard UI
- City/variable selection and playback across forecast horizon
- Toggle between Open-Meteo baseline and model forecast

4. Monitoring and MLOps
- Prometheus scrapes `/metrics`
- Background drift checks compute MAE and update gauges/counters
- GitHub Actions workflow performs periodic drift detection and optional fine-tuning

## Project Structure

```text
backend/
  app/
    main.py
    routes/api.py
    services/
      ml_service.py
      weather_api.py
      forecast_logger.py
      drift_utils.py
      prometheus_drift.py
  models/
    stgnn.py
    stgnn.pt
    stgnn_scaler.pkl
  training/
    train_model.py
    preprocess.py
    data_collector.py
  monitor.py
frontend/
  src/
monitoring/
  prometheus.yml
  alerts.yml
docker-compose.yml
```

## API Endpoints

- `GET /health`
  - Returns backend status and whether model artifacts are loaded.
- `GET /current`
  - Returns latest current conditions for all 7 nodes.
- `GET /forecast`
  - Returns metadata, current snapshot, `openmeteo_forecast`, and `forecast` (STGNN output when ready).
- `GET /metrics`
  - Prometheus metrics, including drift monitoring metrics.
- `GET /docs`
  - Swagger UI.

## Quick Start (Docker Compose)

From repo root:

```bash
docker-compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Prometheus: `http://localhost:9090`

## Local Development (Without Docker)

### 1) Backend

```bash
cd backend
python -m venv venv
```

Activate:

- Windows PowerShell: `venv\Scripts\Activate.ps1`
- Linux/macOS: `source venv/bin/activate`

Install dependencies:

```bash
pip install -r requirements.txt
```

For full STGNN inference/training outside Docker, install PyTorch + PyG stack as well:

```bash
pip install torch==2.1.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install "numpy<2.0.0" "urllib3<2.0.0"
pip install torch-scatter torch-sparse torch-cluster torch-spline-conv torch-geometric -f https://data.pyg.org/whl/torch-2.1.0+cpu.html
```

Run API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` if your backend is not at `http://localhost:8000`.

## Training and Fine-Tuning

From repo root:

Cold start training:

```bash
python -m backend.training.train_model
```

Fine-tuning:

```bash
python -m backend.training.train_model --finetune --epochs 10
```

Fine-tuning with frozen GCN layers:

```bash
python -m backend.training.train_model --finetune --freeze-gcn --epochs 10
```

Training logs and artifacts are tracked in `backend/mlruns` via MLflow.

## Drift Detection

Run CLI drift check:

```bash
python -m backend.monitor --threshold 2.0 --days 7
```

Exit codes:

- `0`: no drift
- `1`: drift detected
- `2`: insufficient data / evaluation not possible

## Prometheus Drift Monitoring

Continuous drift checks run in the backend process and publish metrics.

Environment variables:

- `ENABLE_DRIFT_MONITORING` (default `true`)
- `DRIFT_CHECK_INTERVAL_SECONDS` (default `900`)
- `DRIFT_LOOKBACK_DAYS` (default `7`)
- `DRIFT_MAE_THRESHOLD_C` (default `2.0`)
- `FORECAST_LOG_PATH` (optional path override)

Key metrics:

- `weather_model_drift_overall_mae_celsius`
- `weather_model_drift_city_mae_celsius{city="..."}`
- `weather_model_drift_detected`
- `weather_model_drift_threshold_celsius`
- `weather_model_drift_last_check_status`
- `weather_model_drift_check_total{status="success|insufficient_data|error"}`

Prometheus alert rule is defined in `monitoring/alerts.yml`.

## Scheduled MLOps Workflow

GitHub Actions workflow: `.github/workflows/mlops.yml`

- Schedule: **1st and 15th of each month at 00:00 UTC**
- Runs drift detection
- If drift is detected, collects fresh data and fine-tunes the STGNN
- Pushes updated DVC-tracked model artifacts when successful

## Notes

- If model artifacts are missing, `/forecast` still returns Open-Meteo data, with model forecast empty.
- Backend dependency installation order for PyTorch + PyG is constrained (see `backend/Dockerfile`).
- For reproducible runtime behavior, prefer Docker Compose.
