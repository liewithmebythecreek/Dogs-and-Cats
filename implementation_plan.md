# Real-Time Weather Prediction System

This plan outlines the architecture and implementation steps for building a full-stack real-time weather prediction system. It leverages open-source tools to collect data from Open-Meteo, train an LSTM model on historical data, serve predictions via a FastAPI backend, and display the results on a beautiful React dynamic dashboard. 

> [!NOTE]  
> The system requires no paid APIs. The Open-Meteo API provides extensive historical data for training, and current/forecast data for inference.

## User Review Required

> [!IMPORTANT]
> The daily retraining workflow in GitHub Actions will run automatically based on a cron schedule. The artifacts (newly trained model and scaler) will be committed back to the repository or stored as workflow artifacts. I will implement a simpler approach where the model artifact is saved directly, but please let me know if you prefer to use an external object storage (like AWS S3) for production-grade model registry.
> 
> Also, please confirm if deploying the backend via Docker on Render/Railway using standard Python environments is acceptable for the TensorFlow dependency weight, or if you prefer a quantized model approach.

## Proposed Changes

We will adopt a monorepo structure under `d:/disk d/Weather-Forecast`.

### 1. Root & Configuration
#### [NEW] `docker-compose.yml`
Local orchestration to run both frontend and backend concurrently.
#### [NEW] `README.md`
Complete documentation including architecture details, local setup instruction, deployment flow, and API endpoints.
#### [NEW] `.env.example`
Templates for necessary environment variables (e.g., frontend backend URL, backend CORS domains).

### 2. Machine Learning Pipeline (`backend/training/`)
The ML pipeline runs continuously to ensure the model stays up-to-date with recent weather trends.
#### [NEW] `backend/requirements.txt`
Dependencies including `fastapi`, `uvicorn`, `pandas`, `scikit-learn`, `tensorflow`, `requests`, `httpx`.
#### [NEW] `backend/training/data_collector.py`
Functions to fetch multiple years of historical data from Open-Meteo Historical API.
#### [NEW] `backend/training/preprocess.py`
Data cleaning and transformation. Handles filling NaNs, creating sliding window blocks, and normalizing using `MinMaxScaler`.
#### [NEW] `backend/training/train_model.py`
Defines and trains the LSTM network (Keras/TensorFlow). Configured to evaluate on MAE and RMSE, using early stopping, and saving the final model `.h5` and `scaler.pkl` to `backend/models/`.

### 3. FastAPI Backend (`backend/app/`)
Serves as the bridge between Open-Meteo APIs, the ML model, and the frontend.
#### [NEW] `backend/app/main.py`
FastAPI core app with CORS configuration and endpoint inclusion.
#### [NEW] `backend/app/services/weather_api.py`
Functions to interact with Open-Meteo Geocoding, Current Weather, and Forecast APIs using `httpx`.
#### [NEW] `backend/app/services/ml_service.py`
Loads the `scaler.pkl` and `model.h5` upon application startup. Takes recent hourly weather data from Open-Meteo, preprocesses it, and runs inference to generate short-term predictions.
#### [NEW] `backend/app/routes/api.py`
Exposes the required routes:
- `GET /current/{lat}/{lon}`
- `GET /forecast/{lat}/{lon}`
- `POST /predict` (accepts sequence of recent weather)
- `GET /health`
- `GET /locations/search?q={city}`
#### [NEW] `backend/Dockerfile`
Containerizes the backend using a lightweight Python image.

### 4. React Frontend (`frontend/`)
A dynamic dashboard using Vite, React, Tailwind CSS, and Recharts.
#### [NEW] Vite + React Scaffolding
Standard boilerplate, `package.json` with dependencies (e.g., `axios`, `recharts`, `lucide-react`, `tailwindcss`).
#### [NEW] `frontend/src/services/api.js`
API client configured to point to the backend service.
#### [NEW] `frontend/src/components/WeatherDashboard.jsx`
Main layout, handling location search and geolocation browser API integration.
#### [NEW] `frontend/src/components/WeatherCard.jsx`
Displays current weather nicely formatted with relevant icons based on the weather code.
#### [NEW] `frontend/src/components/ForecastCharts.jsx`
Line charts built with Recharts to plot API's hourly forecast against our LSTM model's predictions over the same time horizon (e.g., comparing temp, humidity).
#### [NEW] `frontend/Dockerfile` & `frontend/nginx.conf`
Multi-stage build compiling React into static assets served via Nginx.

### 5. Automation & CI/CD (`.github/workflows/`)
#### [NEW] `.github/workflows/tests.yml`
Runs pytest on the backend and vitest/linting on the frontend.
#### [NEW] `.github/workflows/retrain.yml`
A scheduled cron job to run the Python training scripts and save updated model artifacts.
#### [NEW] `.github/workflows/deploy.yml`
Deployment strategies to free tiers (e.g., Render for Docker Backend, Vercel/Netlify for Frontend static builds).

## Open Questions

1. **Retraining Frequency:** Do you want the GitHub Actions cron to run the training daily or weekly? Daily might take a long time on the free GitHub Actions runner depending on the total years of history.
2. **Features for LSTM:** I will use Temperature, Humidity, Wind Speed, and Surface Pressure as the core sequential features. Let me know if you would like me to incorporate anything else.

## Verification Plan

### Automated Tests
- Writing basic `pytest` tests for the FastAPI routes.
- The CI pipeline will ensure the code builds correctly and tests pass.

### Manual Verification
1. We will bring the system up using `docker-compose up --build`.
2. I will test the API endpoints directly via `/docs` (Swagger UI).
3. I will test the frontend location search, ensure weather data populates, and that the Recharts components smoothly render the actual Open-Meteo forecast and LSTM predictions.

## UI/UX Redesign Plan

Currently, the frontend suffers from missing Tailwind CSS injections, resulting in a completely unstyled interface. To meet the standard of a truly **stunning, premium dashboard**, I will execute the following redesign steps:

### 1. Tailwind v3 Re-Architecture
Per your request, I will remove all Tailwind v4 dependencies and configurations. I will install `tailwindcss@^3.4.1`, `postcss`, and `autoprefixer`.
- **[DELETE]** Remove `@tailwindcss/vite`.
- **[NEW]** `tailwind.config.js` and `postcss.config.js` will be created to configure Tailwind 3 properly for Vite.
- **[MODIFY]** `vite.config.js` will be reverted to standard React configuration without explicitly importing the Tailwind plugin.
- **[MODIFY]** `index.css` will be rewritten to use the standard `@tailwind base; @tailwind components; @tailwind utilities;` directives, moving all custom animations and theme variables (like glassmorphism) into `tailwind.config.js`.

### 2. Premium Visual Aesthetics
- **Dynamic Backgrounds**: Implement a beautiful glassmorphic dark theme (e.g., blurred atmospheric background gradients) rather than a solid slate color.
- **Typography & Layout**: Upgrade to a modern font (like Inter or Outfit), and implement a clean, responsive grid layout for the Search Bar, Current Weather Card, and Forecast Charts.
- **Micro-animations**: Integrate subtle hover states, smooth transitions for dynamic data loading, and staggered entrance animations.

### 3. Skeleton Loaders & Empty States
Instead of an abrupt "no data" view when the backend is unreachable or loading, I will implement elegant skeleton loaders to preserve the layout structure.

> [!IMPORTANT]
> Please review this UI/UX redesign proposal. Once approved, I will implement the Tailwind fixes and the premium styling!
