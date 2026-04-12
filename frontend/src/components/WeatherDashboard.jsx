import React, { useState, useEffect, useCallback } from 'react';
import { Loader2, Network, RefreshCw } from 'lucide-react';
import { getCurrentConditions, getGraphForecast, CITY_NAMES, DEFAULT_CITY } from '../services/api';
import WeatherCard from './WeatherCard';
import ForecastCharts from './ForecastCharts';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// city → rough description shown in the selector pill
const CITY_META = {
  Ropar:      { label: 'Ropar',      region: 'Punjab' },
  Chandigarh: { label: 'Chandigarh', region: 'UT' },
  Ludhiana:   { label: 'Ludhiana',   region: 'Punjab' },
  Patiala:    { label: 'Patiala',    region: 'Punjab' },
  Jalandhar:  { label: 'Jalandhar',  region: 'Punjab' },
  Ambala:     { label: 'Ambala',     region: 'Haryana' },
  Shimla:     { label: 'Shimla',     region: 'H.P.' },
};

const WeatherDashboard = () => {
  const [currentData,  setCurrentData]  = useState(null);   // {city: {temp,...}}
  const [forecastData, setForecastData] = useState(null);   // full API response
  const [selectedCity, setSelectedCity] = useState(DEFAULT_CITY);
  const [loading,      setLoading]      = useState(false);
  const [lastUpdated,  setLastUpdated]  = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      const [current, graph] = await Promise.all([
        getCurrentConditions(),
        getGraphForecast(),
      ]);
      setCurrentData(current);
      setForecastData(graph);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('[WeatherDashboard] fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Derived slices for the selected city
  const cityWeather  = currentData?.[selectedCity]  ?? null;
  const cityForecast = forecastData?.forecast?.[selectedCity] ?? [];

  return (
    <div className="relative z-10 p-4 md:p-8 selection:bg-blue-500/30">
      <div className="max-w-7xl mx-auto space-y-8 animate-fade-in">

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <Card className="bg-slate-900/60 backdrop-blur-md border-white/10 p-4 md:p-6 shadow-2xl">
          <div className="flex flex-col lg:flex-row justify-between items-center gap-6">

            {/* Brand */}
            <div className="flex-shrink-0 text-center lg:text-left">
              <h1
                className="text-4xl md:text-5xl font-extrabold tracking-tight bg-clip-text text-transparent
                           bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 inline-block text-glow"
                style={{ fontFamily: 'Outfit, sans-serif' }}
              >
                NeuralWeather
              </h1>
              <p className="text-blue-200/80 mt-2 font-medium tracking-wide flex items-center justify-center lg:justify-start gap-2">
                <Network className="w-4 h-4 text-emerald-400" />
                <span>7-Node Punjab · Graph-LSTM · 48 h Forecast</span>
                <span className="relative flex h-3 w-3 ml-1">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
                </span>
              </p>
            </div>

            {/* Refresh + last update */}
            <div className="flex items-center gap-3">
              {lastUpdated && (
                <span className="text-slate-500 text-sm">Updated {lastUpdated}</span>
              )}
              <button
                onClick={fetchAll}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-full bg-blue-600/20 hover:bg-blue-600/30
                           border border-blue-500/30 text-blue-100 text-sm font-semibold transition-all
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>

          {/* ── City selector ──────────────────────────────────────────── */}
          <div className="mt-6 flex flex-wrap gap-2">
            {CITY_NAMES.map(city => (
              <button
                key={city}
                onClick={() => setSelectedCity(city)}
                className={[
                  'px-4 py-1.5 rounded-full text-sm font-semibold border transition-all',
                  selectedCity === city
                    ? 'bg-blue-600/40 border-blue-400/60 text-blue-100 shadow-lg shadow-blue-500/10'
                    : 'bg-slate-800/60 border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-200',
                ].join(' ')}
              >
                {CITY_META[city].label}
                <span className="ml-1.5 text-xs opacity-60">{CITY_META[city].region}</span>
              </button>
            ))}
          </div>
        </Card>

        {/* ── Loading ──────────────────────────────────────────────────────── */}
        {loading && !currentData && (
          <Card className="h-[300px] flex flex-col justify-center items-center gap-4 bg-slate-900/40 border-white/5">
            <Loader2 className="w-12 h-12 text-blue-400 animate-spin" />
            <p className="text-slate-400 font-medium">Fetching 7-node graph data…</p>
          </Card>
        )}

        {/* ── Main content ─────────────────────────────────────────────────── */}
        {currentData && (
          <div className="animate-slide-up">
            <Tabs defaultValue="overview" className="w-full space-y-6">
              <TabsList className="grid w-full grid-cols-2 max-w-[400px] bg-slate-900/80 border border-white/10
                                   p-1 rounded-full mx-auto lg:mx-0">
                <TabsTrigger
                  value="overview"
                  className="rounded-full data-[state=active]:bg-blue-600/30 data-[state=active]:text-blue-100
                             data-[state=active]:shadow-sm transition-all text-slate-300"
                >
                  Current
                </TabsTrigger>
                <TabsTrigger
                  value="analytics"
                  className="rounded-full data-[state=active]:bg-indigo-600/30 data-[state=active]:text-indigo-100
                             data-[state=active]:shadow-sm transition-all text-slate-300"
                >
                  48 h Forecast
                </TabsTrigger>
              </TabsList>

              {/* Current conditions */}
              <TabsContent value="overview" className="space-y-6 mt-4">
                {cityWeather && (
                  <WeatherCard current={cityWeather} locationName={selectedCity} />
                )}
              </TabsContent>

              {/* Forecast charts */}
              <TabsContent value="analytics" className="mt-4">
                <Card className="bg-slate-900/40 backdrop-blur-md border-white/10 shadow-2xl relative overflow-hidden p-1">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl -mr-20 -mt-20" />
                  <CardContent className="p-4 md:p-6 relative z-10 pt-6">
                    <div className="mb-6 flex items-center gap-3">
                      <div className="h-8 w-1 bg-gradient-to-b from-blue-400 to-emerald-400 rounded-full" />
                      <h3
                        className="text-2xl font-bold bg-clip-text text-transparent
                                   bg-gradient-to-r from-blue-100 to-indigo-200"
                        style={{ fontFamily: 'Outfit, sans-serif' }}
                      >
                        Graph-LSTM Forecast · {selectedCity}
                      </h3>
                    </div>
                    <ForecastCharts
                      forecastSteps={cityForecast}
                      cityName={selectedCity}
                    />
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        )}
      </div>
    </div>
  );
};

export default WeatherDashboard;
