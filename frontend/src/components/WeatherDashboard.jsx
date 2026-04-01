import React, { useState, useEffect } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { getCurrentWeather, getForecastWeather, searchLocation } from '../services/api';
import WeatherCard from './WeatherCard';
import ForecastCharts from './ForecastCharts';

const WeatherDashboard = () => {
    const [query, setQuery] = useState('');
    const [location, setLocation] = useState({ lat: 52.52, lon: 13.41, name: "Berlin" }); // Default
    const [currentWeather, setCurrentWeather] = useState(null);
    const [forecastData, setForecastData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [mlReady, setMlReady] = useState(false);

    useEffect(() => {
        fetchData();
    }, [location]);

    const fetchData = async () => {
        try {
            setLoading(true);
            const current = await getCurrentWeather(location.lat, location.lon);
            const forecast = await getForecastWeather(location.lat, location.lon);
            
            setCurrentWeather(current);
            setForecastData(forecast);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query) return;
        
        try {
            const results = await searchLocation(query);
            if (results && results.length > 0) {
                const bestMatch = results[0];
                setLocation({
                    lat: bestMatch.latitude,
                    lon: bestMatch.longitude,
                    name: bestMatch.name + (bestMatch.country ? `, ${bestMatch.country}` : "")
                });
                setQuery('');
            } else {
                alert("City not found.");
            }
        } catch (err) {
            console.error(err);
        }
    };

    const useGeolocation = () => {
        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(
                position => {
                    setLocation({
                        lat: position.coords.latitude,
                        lon: position.coords.longitude,
                        name: "Your Location"
                    });
                },
                err => {
                    alert("Gelocation failed or denied.");
                }
            );
        } else {
            alert("Geolocation not supported by this browser.");
        }
    };

    return (
        <div className="relative z-10 p-4 md:p-8 selection:bg-blue-500/30">
            <div className="max-w-7xl mx-auto space-y-8 animate-fade-in">
                
                {/* Header & Search */}
                <div className="glass-card p-6 md:px-8 flex flex-col lg:flex-row justify-between items-center gap-6">
                    <div className="flex-1 text-center lg:text-left">
                        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 inline-block text-glow" style={{fontFamily: 'Outfit, sans-serif'}}>
                            NeuralWeather
                        </h1>
                        <p className="text-blue-200/80 mt-2 font-medium tracking-wide flex items-center justify-center lg:justify-start gap-2">
                            <span className="relative flex h-3 w-3">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                            </span>
                            Live ML Forecaster Active
                        </p>
                    </div>

                    <div className="flex-1 w-full max-w-xl">
                        <form onSubmit={handleSearch} className="relative flex items-center w-full group">
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Search for a city..."
                                className="w-full bg-slate-900/50 backdrop-blur-md border border-white/10 text-white placeholder-slate-400 rounded-full py-4 px-6 pl-14 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-400/50 transition-all shadow-inner group-hover:bg-slate-900/70"
                                style={{fontFamily: 'Inter, sans-serif'}}
                            />
                            <Search className="absolute left-5 text-slate-400 w-5 h-5 group-hover:text-blue-400 transition-colors" />
                            <button type="submit" className="hidden">Submit</button>
                            <button 
                                type="button"
                                onClick={useGeolocation}
                                className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600/90 hover:bg-blue-500 text-white px-4 py-2 rounded-full text-sm font-semibold transition-all shadow-lg hover:shadow-blue-500/40 whitespace-nowrap"
                            >
                                Locate Me
                            </button>
                        </form>
                    </div>
                </div>

                {/* Dashboard Loading State */}
                {loading ? (
                    <div className="animate-pulse space-y-6">
                        <div className="glass-card h-[300px] w-full flex flex-col justify-center items-center gap-4">
                            <Loader2 className="w-12 h-12 text-blue-400 animate-spin" />
                            <p className="text-slate-400 font-medium">Crunching data & running inference...</p>
                        </div>
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className="glass-card h-[400px] w-full"></div>
                            <div className="glass-card h-[400px] w-full"></div>
                        </div>
                    </div>
                ) : !currentWeather && !forecastData ? (
                    /* Initial Empty State */
                    <div className="glass-card h-[400px] flex flex-col items-center justify-center text-center p-8 animate-slide-up">
                        <div className="w-24 h-24 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-full flex items-center justify-center mb-6 border border-white/5">
                            <Search className="w-10 h-10 text-blue-400" />
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-2" style={{fontFamily: 'Outfit, sans-serif'}}>Ready to Predict</h2>
                        <p className="text-slate-400 max-w-md">Search for any location globally to see real-time Open-Meteo metrics alongside our advanced LSTM model's hyper-local forecasts.</p>
                    </div>
                ) : (
                    <div className="space-y-6 animate-slide-up">
                        {currentWeather && (
                            <div className="glass-card overflow-hidden">
                                <WeatherCard current={currentWeather} locationName={location.name} />
                            </div>
                        )}

                        {forecastData && (
                            <div className="glass-card p-6 border-t border-white/5 shadow-2xl relative overflow-hidden">
                                <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl -mr-20 -mt-20"></div>
                                <div className="relative z-10">
                                    <div className="mb-6 flex items-center gap-3">
                                        <div className="h-8 w-1 bg-gradient-to-b from-blue-400 to-emerald-400 rounded-full"></div>
                                        <h3 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-100 to-indigo-200" style={{fontFamily: 'Outfit, sans-serif'}}>
                                            Predictive Analytics
                                        </h3>
                                    </div>
                                    <ForecastCharts 
                                        forecast={forecastData} 
                                        mlPredictions={forecastData.ml_predictions} 
                                    />
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default WeatherDashboard;
