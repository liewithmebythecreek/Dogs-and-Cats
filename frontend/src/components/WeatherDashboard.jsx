import React, { useState, useEffect } from 'react';
import { Search, Loader2, MapPin } from 'lucide-react';
import { getCurrentWeather, getForecastWeather, searchLocation } from '../services/api';
import WeatherCard from './WeatherCard';
import ForecastCharts from './ForecastCharts';
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const WeatherDashboard = () => {
    const [query, setQuery] = useState('');
    const [location, setLocation] = useState({ lat: 52.52, lon: 13.41, name: "Berlin" }); // Default
    const [currentWeather, setCurrentWeather] = useState(null);
    const [forecastData, setForecastData] = useState(null);
    const [loading, setLoading] = useState(false);

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
                <Card className="bg-slate-900/60 backdrop-blur-md border-white/10 p-4 md:p-6 shadow-2xl">
                    <div className="flex flex-col lg:flex-row justify-between items-center gap-6">
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
                            <form onSubmit={handleSearch} className="flex gap-2 w-full">
                                <div className="relative w-full">
                                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5 z-10" />
                                    <Input
                                        type="text"
                                        value={query}
                                        onChange={(e) => setQuery(e.target.value)}
                                        placeholder="Search for a city..."
                                        className="w-full bg-slate-950/50 border-white/10 text-white placeholder:text-slate-400 rounded-full h-12 pl-12 pr-4 focus-visible:ring-blue-500/50"
                                        style={{fontFamily: 'Inter, sans-serif'}}
                                    />
                                </div>
                                <Button 
                                    type="button" 
                                    onClick={useGeolocation}
                                    variant="secondary"
                                    className="rounded-full h-12 px-6 bg-blue-600/20 hover:bg-blue-600/30 text-blue-100 border-blue-500/30 transition-all font-semibold"
                                >
                                    <MapPin className="w-4 h-4 mr-2" />
                                    Locate
                                </Button>
                                <Button type="submit" className="hidden">Submit</Button>
                            </form>
                        </div>
                    </div>
                </Card>

                {/* Dashboard Loading State */}
                {loading ? (
                    <div className="animate-pulse space-y-6">
                        <Card className="h-[300px] w-full flex flex-col justify-center items-center gap-4 bg-slate-900/40 border-white/5">
                            <Loader2 className="w-12 h-12 text-blue-400 animate-spin" />
                            <p className="text-slate-400 font-medium">Crunching data & running inference...</p>
                        </Card>
                    </div>
                ) : !currentWeather && !forecastData ? (
                    /* Initial Empty State */
                    <Card className="h-[400px] flex flex-col items-center justify-center text-center p-8 bg-slate-900/40 border-white/5 animate-slide-up shadow-2xl">
                        <div className="w-24 h-24 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-full flex items-center justify-center mb-6 border border-white/5 shadow-inner">
                            <Search className="w-10 h-10 text-blue-400" />
                        </div>
                        <h2 className="text-3xl font-bold text-white mb-2" style={{fontFamily: 'Outfit, sans-serif'}}>Ready to Predict</h2>
                        <p className="text-slate-400 max-w-md text-lg">Search for any location globally to see real-time Open-Meteo metrics alongside our advanced LSTM model's hyper-local forecasts.</p>
                    </Card>
                ) : (
                    <div className="animate-slide-up">
                        <Tabs defaultValue="overview" className="w-full space-y-6">
                            <TabsList className="grid w-full grid-cols-2 max-w-[400px] bg-slate-900/80 border border-white/10 p-1 rounded-full mx-auto lg:mx-0">
                                <TabsTrigger value="overview" className="rounded-full data-[state=active]:bg-blue-600/30 data-[state=active]:text-blue-100 data-[state=active]:shadow-sm transition-all text-slate-300">Overview</TabsTrigger>
                                <TabsTrigger value="analytics" className="rounded-full data-[state=active]:bg-indigo-600/30 data-[state=active]:text-indigo-100 data-[state=active]:shadow-sm transition-all text-slate-300">Analytics</TabsTrigger>
                            </TabsList>
                            
                            <TabsContent value="overview" className="space-y-6 mt-4">
                                {currentWeather && (
                                    <WeatherCard current={currentWeather} locationName={location.name} />
                                )}
                            </TabsContent>
                            
                            <TabsContent value="analytics" className="mt-4">
                                {forecastData && (
                                    <Card className="bg-slate-900/40 backdrop-blur-md border-white/10 shadow-2xl relative overflow-hidden p-1">
                                        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl -mr-20 -mt-20"></div>
                                        <CardContent className="p-4 md:p-6 relative z-10 pt-6">
                                            <div className="mb-6 flex items-center gap-3">
                                                <div className="h-8 w-1 bg-gradient-to-b from-blue-400 to-emerald-400 rounded-full"></div>
                                                <h3 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-100 to-indigo-200" style={{fontFamily: 'Outfit, sans-serif'}}>
                                                    Predictive Analytics Model
                                                </h3>
                                            </div>
                                            <ForecastCharts 
                                                forecast={forecastData} 
                                                mlPredictions={forecastData.ml_predictions} 
                                            />
                                        </CardContent>
                                    </Card>
                                )}
                            </TabsContent>
                        </Tabs>
                    </div>
                )}
            </div>
        </div>
    );
};

export default WeatherDashboard;
