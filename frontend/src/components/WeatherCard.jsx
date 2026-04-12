import React from 'react';
import { CloudRain, Wind, Thermometer, Droplets, Gauge } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const WeatherCard = ({ current, locationName }) => {
  if (!current) return null;

  return (
    <Card className="w-full h-full bg-slate-900/40 backdrop-blur-md border-white/10 shadow-2xl overflow-hidden relative">
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl -mr-20 -mt-20"></div>
      
      <CardHeader className="relative z-10 pb-2 md:pb-4 space-y-4">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center">
          <div>
            <CardTitle className="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-100 to-indigo-200 tracking-tight" style={{fontFamily: 'Outfit, sans-serif'}}>
              {locationName || "Current Location"}
            </CardTitle>
            <div className="flex items-center gap-2 mt-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              <p className="text-emerald-400/80 text-sm font-medium tracking-wide uppercase">Live Conditions</p>
            </div>
          </div>
          <div className="flex flex-col items-end mt-4 md:mt-0">
            <div className="text-6xl md:text-7xl font-extrabold text-white tracking-tighter" style={{fontFamily: 'Outfit, sans-serif'}}>
              <span className="text-transparent bg-clip-text bg-gradient-to-br from-white to-blue-200 drop-shadow-lg">
                  {current.temperature_2m}°
              </span>
              <span className="text-3xl text-blue-300/50">C</span>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-4 relative z-10 w-full pt-4 border-t border-white/10">
        {/* Metric 1 */}
        <div className="flex items-center space-x-4 bg-white/5 hover:bg-white/10 p-4 rounded-2xl transition-colors border border-white/5 backdrop-blur-sm group py-5">
          <div className="p-3 bg-orange-500/20 rounded-xl group-hover:scale-110 transition-transform">
              <Thermometer className="text-orange-400 w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-wider mb-1">Temp</p>
            <p className="text-xl font-semibold text-slate-100">{current.temperature_2m}°C</p>
          </div>
        </div>
        
        {/* Metric 2 */}
        <div className="flex items-center space-x-4 bg-white/5 hover:bg-white/10 p-4 rounded-2xl transition-colors border border-white/5 backdrop-blur-sm group py-5">
          <div className="p-3 bg-blue-500/20 rounded-xl group-hover:scale-110 transition-transform">
              <Droplets className="text-blue-400 w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-wider mb-1">Humidity</p>
            <p className="text-xl font-semibold text-slate-100">{current.relative_humidity_2m}%</p>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="flex items-center space-x-4 bg-white/5 hover:bg-white/10 p-4 rounded-2xl transition-colors border border-white/5 backdrop-blur-sm group py-5">
          <div className="p-3 bg-emerald-500/20 rounded-xl group-hover:scale-110 transition-transform">
              <Wind className="text-emerald-400 w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-wider mb-1">Wind</p>
            <p className="text-xl font-semibold text-slate-100">{current.wind_speed_10m} <span className="text-sm text-slate-400">km/h</span></p>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="flex items-center space-x-4 bg-white/5 hover:bg-white/10 p-4 rounded-2xl transition-colors border border-white/5 backdrop-blur-sm group py-5">
          <div className="p-3 bg-purple-500/20 rounded-xl group-hover:scale-110 transition-transform">
              <Gauge className="text-purple-400 w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-wider mb-1">Pressure</p>
            <p className="text-xl font-semibold text-slate-100">{current.surface_pressure} <span className="text-sm text-slate-400">hPa</span></p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default WeatherCard;
