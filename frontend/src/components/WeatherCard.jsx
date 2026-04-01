import React from 'react';
import { CloudRain, Wind, Thermometer, Droplets, Gauge } from 'lucide-react';

const WeatherCard = ({ current, locationName }) => {
  if (!current) return null;

  return (
    <div className="w-full h-full p-8 flex flex-col justify-between relative">
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl -mr-20 -mt-20"></div>
      
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center relative z-10 space-y-4 md:space-y-0">
        <div>
          <h2 className="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-100 to-indigo-200 tracking-tight" style={{fontFamily: 'Outfit, sans-serif'}}>
            {locationName || "Current Location"}
          </h2>
          <div className="flex items-center gap-2 mt-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500"></span>
            </span>
            <p className="text-blue-200/70 text-sm font-medium tracking-wide uppercase">Live Conditions</p>
          </div>
        </div>
        
        <div className="flex flex-col items-end">
          <div className="text-6xl md:text-7xl font-extrabold text-white tracking-tighter" style={{fontFamily: 'Outfit, sans-serif'}}>
            <span className="text-transparent bg-clip-text bg-gradient-to-br from-white to-blue-200 drop-shadow-lg">
                {current.temperature_2m}°
            </span>
            <span className="text-3xl text-blue-300/50">C</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-8 mt-8 border-t border-white/10 relative z-10 w-full">
        {/* Metric 1 */}
        <div className="flex items-center space-x-4 bg-white/5 hover:bg-white/10 p-4 rounded-2xl transition-colors border border-white/5 backdrop-blur-sm group">
          <div className="p-3 bg-orange-500/20 rounded-xl group-hover:scale-110 transition-transform">
              <Thermometer className="text-orange-400 w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-wider mb-1">Temp</p>
            <p className="text-xl font-semibold text-slate-100">{current.temperature_2m}°C</p>
          </div>
        </div>
        
        {/* Metric 2 */}
        <div className="flex items-center space-x-4 bg-white/5 hover:bg-white/10 p-4 rounded-2xl transition-colors border border-white/5 backdrop-blur-sm group">
          <div className="p-3 bg-blue-500/20 rounded-xl group-hover:scale-110 transition-transform">
              <Droplets className="text-blue-400 w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-wider mb-1">Humidity</p>
            <p className="text-xl font-semibold text-slate-100">{current.relative_humidity_2m}%</p>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="flex items-center space-x-4 bg-white/5 hover:bg-white/10 p-4 rounded-2xl transition-colors border border-white/5 backdrop-blur-sm group">
          <div className="p-3 bg-emerald-500/20 rounded-xl group-hover:scale-110 transition-transform">
              <Wind className="text-emerald-400 w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-wider mb-1">Wind</p>
            <p className="text-xl font-semibold text-slate-100">{current.wind_speed_10m} <span className="text-sm text-slate-400">km/h</span></p>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="flex items-center space-x-4 bg-white/5 hover:bg-white/10 p-4 rounded-2xl transition-colors border border-white/5 backdrop-blur-sm group">
          <div className="p-3 bg-purple-500/20 rounded-xl group-hover:scale-110 transition-transform">
              <Gauge className="text-purple-400 w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-wider mb-1">Pressure</p>
            <p className="text-xl font-semibold text-slate-100">{current.surface_pressure} <span className="text-sm text-slate-400">hPa</span></p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WeatherCard;
