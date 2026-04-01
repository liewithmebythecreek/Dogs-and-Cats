# Real-Time Weather Prediction System

A complete full-stack Real-Time Weather Prediction System that leverages the **Open-Meteo API** to fetch historical and current weather data, trains an **LSTM neural network** for time-series forecasting, and displays everything on a beautiful **React (Vite)** dashboard.

## 🌟 Key Features

1. **Free & Open-Source Pipeline:** Uses only free Open-Meteo APIs—no API keys required.
2. **Machine Learning Model:** LSTM time-series regression model trained on years of historical weather data. Core parameters: Temperature, Humidity, Wind Speed, Pressure, and Precipitation Probability.
3. **Automated ML DevOps:** A GitHub Actions Cron workflow continuously retrains the model on recent data and commits the updated weights.
4. **FastAPI Backend:** A fast, asynchronous backend that serves live Open-Meteo data merged with our custom ML predictions.
5. **Modern Dashboard:** React (Vite) + Tailwind CSS + Recharts visualizer. Features location search, browser geolocation tracking, current weather stats, and beautiful data comparison charts.

## 🏗️ Architecture Stack

- **ML Pipeline:** Python, Keras/TensorFlow, scikit-learn (MinMaxScaler), Pandas.
- **Backend:** FastAPI, Uvicorn, httpx.
- **Frontend:** React, Vite, Tailwind CSS, Recharts, Axios.
- **Infra/DevOps:** Docker, Docker Compose, GitHub Actions.

## 🚀 Quick Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/weather-prediction-system.git
   cd weather-prediction-system
   ```

2. **Setup environment variables:**
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` if you need to run on different ports.*

3. **Start with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

4. **Access the Application:**
   - Frontend Dashboard: `http://localhost:3000`
   - Backend API Docs: `http://localhost:8000/docs`

## 🧠 ML Training Commands

If you wish to train the LSTM model locally without using the automated workflow or Docker container:

```bash
cd backend
python -m venv venv
# Linux/Mac
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt
python -m training.train_model
```
*This will fetch data, preprocess it, train the model, and save `model.h5` and `scaler.pkl` to `backend/models/`.*

## 🛣️ API Endpoints Summary

- `GET /current/{lat}/{lon}`: Fetches current combined weather metrics.
- `GET /forecast/{lat}/{lon}`: Fetches official Open-Meteo forecast combined with the ML predictions for the timeframe.
- `GET /locations/search?q={city}`: Simple Open-Meteo geocoding wrapper to search for lat/lon.
- `POST /predict`: Direct access to ML predictions based on uploaded recent sequence block.
