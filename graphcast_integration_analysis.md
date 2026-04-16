# GraphCast Integration Analysis for NeuralWeather

## 1. What GraphCast Is

GraphCast is a **Graph Neural Network (GNN) based global weather forecasting model** published by Google DeepMind in *Science* (2023). It predicts weather at **global scale** (0.25° or 1° resolution) using ERA5/HRES reanalysis data as inputs, producing **6-hour step forecasts** up to 10 days ahead. It operates entirely in **JAX** (not TensorFlow/Keras), using the **Haiku** neural network library.

---

## 2. Repository Structure (cloned to `d:\disk d\graphcast-repo`)

```
graphcast-repo/
├── graphcast/
│   ├── graphcast.py         # Core GraphCast GNN model (Encoder → Processor → Decoder)
│   ├── gencast.py           # GenCast diffusion-based ensemble model
│   ├── rollout.py           # Autoregressive multi-step inference engine
│   ├── checkpoint.py        # .npz weight serialiser/deserialiser
│   ├── data_utils.py        # xarray preprocessing, forcing variables (TISR, day/year progress)
│   ├── normalization.py     # Input/target normalisation from ERA5 statistics
│   ├── autoregressive.py    # Differentiable autoregressive wrapper (for training)
│   ├── model_utils.py       # Grid↔Mesh projection utilities
│   ├── grid_mesh_connectivity.py  # Icosahedral mesh↔lat-lon grid mapping
│   ├── icosahedral_mesh.py  # Multi-level triangular mesh
│   ├── losses.py            # Latitude-weighted MSE loss
│   └── solar_radiation.py   # Top-of-atmosphere solar radiation (forcing var)
├── graphcast_demo.ipynb     # Official inference demo notebook
├── gencast_mini_demo.ipynb  # GenCast demo (runnable in free Colab)
└── setup.py                 # pip install deps
```

---

## 3. GraphCast Architecture Deep-Dive

```
Input xarray.Dataset (ERA5 grid, lat/lon/level/time)
      │
      ▼  Encoder (Grid → Mesh)
  grid2mesh_gnn  ──── single GNN message-passing step
      │              maps 0.25° grid nodes → icosahedral mesh nodes
      ▼
  Mesh Processor (Mesh → Mesh)
  mesh_gnn  ──── N message-passing steps (e.g. 16 for full model)
      │          propagates atmospheric state across the globe
      ▼
  Decoder (Mesh → Grid)
  mesh2grid_gnn  ──── single GNN message passing
      │               maps mesh back to 0.25° output grid
      ▼
Output xarray.Dataset (one 6h step forward)
      │
      └──(autoregressive loop via rollout.py)──► multi-day forecast
```

**Key data types needed:**
| Variable Category | Examples |
|---|---|
| Surface vars (target) | `2m_temperature`, `mean_sea_level_pressure`, `10m_u/v_component_of_wind`, `total_precipitation_6hr` |
| Atmospheric vars (target) | `temperature`, `geopotential`, `specific_humidity`, `u/v_component_of_wind`, `vertical_velocity` — at 13/25/37 pressure levels |
| Forcing vars | `toa_incident_solar_radiation`, `year_progress_sin/cos`, `day_progress_sin/cos` |
| Static vars | `geopotential_at_surface`, `land_sea_mask` |

**Input format:** `xarray.Dataset` with dimensions `(batch, time=2, lat, lon, level)` — **exactly 2 time frames** at t-6h and t±0 (12-hour input window).

---

## 4. Pre-trained Weights (from Google Cloud Bucket)

| Model | Resolution | Pressure Levels | GCS Path | ~Size |
|---|---|---|---|---|
| `GraphCast` | 0.25° | 37 | `gs://dm_graphcast/graphcast/` | ~600 MB |
| `GraphCast_small` | 1.0° | 13 | `gs://dm_graphcast/graphcast/` | ~130 MB |
| `GraphCast_operational` | 0.25° | 13 | `gs://dm_graphcast/graphcast/` | ~300 MB |
| `GenCast 1p0deg Mini` | 1.0° | 13 | `gs://dm_graphcast/gencast/` | smallest |

> For local development, **`GraphCast_small` (1°, 13 levels)** is the most practical — runs on a GPU with ~8 GB VRAM or modern CPU (slowly).

---

## 5. Fundamental Compatibility Issues vs. Your Current Stack

| Aspect | Your NeuralWeather (LSTM) | GraphCast |
|---|---|---|
| **Framework** | TensorFlow / Keras | JAX + Haiku |
| **Input data** | 6 surface vars from Open-Meteo API | Full ERA5/HRES (surface + multi-level) |
| **Resolution** | Single point (lat/lon) | Global grid (0.25° or 1°) |
| **Timestep** | 1-hour | 6-hour |
| **Forecast horizon** | 24 hours | Up to 10 days |
| **Model weights** | ~2 MB `.keras` file | 130–600 MB `.npz` checkpoint |
| **RAM at inference** | < 500 MB | 8–32 GB (model dependent) |
| **GPU required** | No (CPU fine) | Strongly recommended (16 GB+) |
| **Data source** | Open-Meteo (free API) | ERA5 / ECMWF HRES (large downloads) |
| **Trainable locally** | Yes (fine-tune daily) | No (requires TPU pods / massive compute) |
| **Latency per inference** | ~100 ms | Minutes to hours without GPU |

> [!WARNING]
> GraphCast is a **global, research-grade model**. It is NOT a drop-in replacement for your LSTM — it is an entirely different scale and stack. Running it locally requires significant RAM/GPU.

---

## 6. Feasible Integration Strategies

### Strategy A — GraphCast as a High-Quality "Remote Oracle" (Recommended ✅)
Use the **official GraphCast API** (Google's Weather API or third-party wrappers) rather than running the model yourself. The model is already deployed; you just query it.

- **Pros:** No GPU needed, no data pipeline, instant integration
- **Cons:** Requires API key / paid account (currently in limited Google access)
- **How:** Add a `graphcast_api_service.py` that calls the GraphCast endpoint and maps its output to your API schema

### Strategy B — Local Inference with `GraphCast_small` Checkpoint (Advanced 🔬)
Download the `GraphCast_small` weights, set up a local JAX inference pipeline, feed ERA5-compatible data (from Open-Meteo or CDS), and run rollout for your target location.

- **Pros:** Free, full control, 10-day forecasts
- **Cons:** Heavyweight setup, 8–16 GB RAM, slow on CPU (~30 min/step), ERA5 data formatting is complex
- **How:** See full plan in Section 8

### Strategy C — Hybrid LSTM + GraphCast Output Blending (Pragmatic 🎯)
Use **GraphCast's public forecast files** (available for free via Open-Meteo's GraphCast layer or ECMWF's open data) as an additional input/reference, while keeping your LSTM for short-range high-frequency predictions.

- **Pros:** Best of both worlds, low complexity, no new dependencies
- **Cons:** Not running GraphCast yourself, dependent on third-party data
- **How:** Open-Meteo already provides GraphCast forecasts via their API!

---

## 7. Recommended Architecture: LSTM + GraphCast Hybrid (Strategy C)

```
                        ┌─────────────────────────────┐
                        │     FastAPI Backend          │
                        └──────────────┬──────────────┘
                                       │
              ┌──────────────┬─────────┴──────────┐
              │              │                    │
    ┌─────────▼────┐  ┌──────▼──────┐  ┌─────────▼────────┐
    │  Open-Meteo  │  │ LSTM Model  │  │ GraphCast Layer  │
    │  Live API    │  │ (short-term │  │ via Open-Meteo   │
    │  (current    │  │  24h LSTM   │  │ GraphCast API    │
    │   weather)   │  │  forecast)  │  │ (10-day medium-  │
    └─────────┬────┘  └──────┬──────┘  │  range GNN fcst) │
              │              │         └─────────┬────────┘
              └──────────────┴──────────────────┘
                                       │
                              ┌────────▼────────┐
                              │   Unified JSON   │
                              │   Response API   │
                              └─────────────────┘
```

**Open-Meteo GraphCast endpoint:** `https://api.open-meteo.com/v1/forecast?models=graphcast_seamless`

This gives you **real GraphCast output** with zero infrastructure overhead.

---

## 8. Local GraphCast Inference Pipeline (Strategy B) — Full Technical Plan

### 8.1 New Dependencies
```txt
# Add to requirements.txt
jax[cpu]               # or jax[cuda12] for GPU
dm-haiku
jraph
chex
dm-tree
xarray
dask
trimesh
scipy
rtree
typing_extensions
cdsapi                 # for ERA5 data download
```

> [!CAUTION]
> JAX conflicts with TensorFlow on some setups. Use a **separate virtual environment** for GraphCast inference.

### 8.2 Data Pipeline — ERA5 → GraphCast xarray Format

GraphCast needs `xarray.Dataset` with specific ERA5-compatible variables. The simplest approach for your single-location project is to use **Open-Meteo pressure-level data** to approximate ERA5.

```python
# backend/training/graphcast_data_prep.py
import xarray as xr
import numpy as np
import pandas as pd

def build_graphcast_input_from_openmeteo(lat: float, lon: float, 
                                          timestamp: pd.Timestamp) -> xr.Dataset:
    """
    Constructs a minimal GraphCast-compatible xarray.Dataset 
    from Open-Meteo API data for a SINGLE grid point.
    
    NOTE: GraphCast was trained on global grids. Single-point inference
    is NOT officially supported and will give degraded results.
    For best results use the full global ERA5 grid.
    """
    # This requires fetching:
    # 1. Surface vars: 2m_temperature, msl_pressure, 10m_u_wind, 10m_v_wind
    # 2. Pressure-level vars at 13 levels: temperature, geopotential, 
    #    specific_humidity, u_wind, v_wind, vertical_velocity
    # 3. Static vars: land_sea_mask, geopotential_at_surface
    # 4. Forcing vars: computed by graphcast.data_utils
    pass
```

### 8.3 Checkpoint Loading

```python
# backend/app/services/graphcast_service.py
import sys
sys.path.insert(0, r"d:\disk d\graphcast-repo")

import haiku as hk
import jax
import jax.numpy as jnp
import xarray as xr
from graphcast import graphcast, checkpoint, normalization, rollout, data_utils

class GraphCastService:
    def __init__(self, checkpoint_path: str):
        # Load the .npz checkpoint
        with open(checkpoint_path, "rb") as f:
            ckpt = checkpoint.load(f, graphcast.CheckPoint)
        
        self.params = ckpt.params
        self.model_config = ckpt.model_config
        self.task_config = ckpt.task_config
        
        # Build the Haiku-transformed model
        def run_forward(inputs, targets_template, forcings):
            return graphcast.GraphCast(
                model_config=self.model_config,
                task_config=self.task_config
            )(inputs, targets_template, forcings)
        
        self._run_forward = hk.transform_with_state(run_forward)
        self._jit_run = jax.jit(self._run_forward.apply)
    
    def predict(self, inputs: xr.Dataset, forcings: xr.Dataset, 
                num_steps: int = 4) -> xr.Dataset:
        """Run autoregressive rollout for num_steps × 6h = 24h default."""
        
        # Add derived forcing variables
        data_utils.add_derived_vars(inputs)
        
        targets_template = rollout.extend_targets_template(
            inputs.isel(time=slice(-1, None)),  # last input frame as template
            required_num_steps=num_steps
        )
        
        def predictor_fn(rng, inputs, targets_template, forcings):
            (predictions, _), _ = self._jit_run(
                self.params, None, rng,
                inputs, targets_template, forcings
            )
            return predictions
        
        predictions = rollout.chunked_prediction(
            predictor_fn=predictor_fn,
            rng=jax.random.PRNGKey(0),
            inputs=inputs,
            targets_template=targets_template,
            forcings=forcings,
        )
        return predictions
```

### 8.4 Output Extraction for Your API

```python
def extract_surface_forecast(predictions: xr.Dataset, lat: float, lon: float) -> list:
    """Extract surface vars for your target location from global GraphCast output."""
    results = []
    for t in range(predictions.dims["time"]):
        step = predictions.isel(time=t).sel(lat=lat, lon=lon, method="nearest")
        results.append({
            "temperature_2m": float(step["2m_temperature"].values) - 273.15,  # K→°C
            "wind_speed_10m": float(np.sqrt(
                step["10m_u_component_of_wind"].values**2 + 
                step["10m_v_component_of_wind"].values**2
            )),
            "surface_pressure": float(step["mean_sea_level_pressure"].values) / 100,  # Pa→hPa
            "precipitation": float(step.get("total_precipitation_6hr", 0).values),
        })
    return results
```

---

## 9. Open-Meteo GraphCast Integration (Strategy C) — Easiest Path

Open-Meteo exposes GraphCast model output directly. Just add one line to your existing weather API service:

```python
# backend/app/services/weather_api.py  — ADD GraphCast model param
GRAPHCAST_URL = "https://api.open-meteo.com/v1/forecast"

async def fetch_graphcast_forecast(lat: float, lon: float, days: int = 10):
    """Fetch 10-day GraphCast forecast via Open-Meteo's GraphCast layer."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "wind_speed_10m_max",
            "weather_code"
        ],
        "hourly": ["temperature_2m", "precipitation", "wind_speed_10m"],
        "models": "graphcast_seamless",   # ← THIS IS THE KEY PARAM
        "forecast_days": days,
        "timezone": "auto"
    }
    # Use your existing openmeteo_requests client
    ...
```

---

## 10. Recommended Integration Roadmap

### Phase 1 — GraphCast via Open-Meteo (1–2 days) ✅ DO THIS FIRST
- Add `graphcast_seamless` model parameter to Open-Meteo calls
- Add a new `/graphcast-forecast` API endpoint in FastAPI
- Display 10-day GNN forecast alongside your 24h LSTM forecast in the UI
- **Zero new dependencies, zero hardware changes**

### Phase 2 — Local GraphCast_small Inference (1–2 weeks) 🔬
- Create a **separate Python environment** with JAX, Haiku, jraph
- Download `GraphCast_small` checkpoint (~130 MB) from `gs://dm_graphcast/`
- Build `graphcast_service.py` (skeleton in Section 8.3)
- Wire up ERA5-approximate data from Open-Meteo pressure levels
- Add `/graphcast-local` endpoint; compare outputs to Phase 1

### Phase 3 — Hybrid Ensemble (Future) 🚀
- Blend LSTM 24h short-range predictions with GraphCast 10-day medium-range
- Weighted ensemble: LSTM for 0–24h, GraphCast for 1–10 days
- Display uncertainty bands using GraphCast ensemble members (GenCast)

---

## 11. Files to Create / Modify

| File | Action | Notes |
|---|---|---|
| `backend/app/services/weather_api.py` | **MODIFY** | Add `graphcast_seamless` model parameter |
| `backend/app/services/graphcast_service.py` | **NEW** | Local JAX inference stub (Phase 2) |
| `backend/app/routes/forecast.py` | **MODIFY** | Add `/graphcast-forecast` endpoint |
| `backend/requirements.txt` | **MODIFY** | Add jax, haiku etc. (Phase 2 only) |
| `backend/training/graphcast_data_prep.py` | **NEW** | ERA5 → xarray converter (Phase 2) |

---

## 12. Key Limitations to Understand

> [!IMPORTANT]
> **GraphCast is not designed for single-point forecasting.** It's trained on the full global ERA5 grid. Extracting a single lat/lon point from its output is valid, but running it on a cropped/single-point input is not. For your use case, you are always **reading a point from global output**, not feeding it a single point.

> [!WARNING]
> **License:** Model weights are **CC BY-NC-SA 4.0** — non-commercial use only. The code is Apache 2.0. Make sure your project stays non-commercial if using the pretrained weights.

> [!NOTE]
> **Python version:** GraphCast requires Python 3.10 or 3.11. Check `python --version` before setting up the JAX environment.
