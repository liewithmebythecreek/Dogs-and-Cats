import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const ForecastCharts = ({ forecast, mlPredictions }) => {
  if (!forecast || !forecast.hourly) return null;

  // Prepare data comparing next 24 hours
  // Usually forecast.hourly.time gives us timestamps
  const chartData = [];
  const limit = 24; // Show next 24 hours

  for (let i = 0; i < limit; i++) {
    const timeFull = new Date(forecast.hourly.time[i]);
    const label = timeFull.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    chartData.push({
      time: label,
      "API Temp": forecast.hourly.temperature_2m[i],
      "LSTM Temp": mlPredictions && mlPredictions.length > i ? mlPredictions[i].temperature_2m : null,
      "API Humidity": forecast.hourly.relative_humidity_2m[i],
      "LSTM Humidity": mlPredictions && mlPredictions.length > i ? mlPredictions[i].relative_humidity_2m : null,
    });
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 w-full mt-4">
      {/* Temperature Chart */}
      <div className="bg-white/5 p-6 rounded-2xl border border-white/5 backdrop-blur-md relative group transition-all hover:bg-white/10">
        <h3 className="text-xl font-semibold bg-clip-text text-transparent bg-gradient-to-r from-orange-200 to-red-200 mb-6 flex items-center gap-2" style={{fontFamily: 'Outfit, sans-serif'}}>
           <div className="w-2 h-2 rounded-full bg-orange-400 animate-pulse"></div>
           Temperature Forecast (24h)
        </h3>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" vertical={false} />
              <XAxis dataKey="time" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} tickLine={false} axisLine={false} dy={10} />
              <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} tickLine={false} axisLine={false} dx={-10} />
              <Tooltip 
                contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: '#f8fafc', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)' }}
                itemStyle={{ color: '#f8fafc', fontWeight: 500 }}
              />
              <Legend wrapperStyle={{ paddingTop: '20px' }} iconType="circle" />
              <Line type="monotone" dataKey="API Temp" name="Open-Meteo" stroke="#3b82f6" strokeWidth={3} dot={false} activeDot={{ r: 6, strokeWidth: 0, fill: '#3b82f6' }} />
              <Line type="monotone" dataKey="LSTM Temp" name="LSTM Model" stroke="#f59e0b" strokeWidth={3} dot={false} strokeDasharray="5 5" activeDot={{ r: 6, strokeWidth: 0, fill: '#f59e0b' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Humidity Chart */}
      <div className="bg-white/5 p-6 rounded-2xl border border-white/5 backdrop-blur-md relative group transition-all hover:bg-white/10">
        <h3 className="text-xl font-semibold bg-clip-text text-transparent bg-gradient-to-r from-cyan-200 to-blue-200 mb-6 flex items-center gap-2" style={{fontFamily: 'Outfit, sans-serif'}}>
           <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></div>
           Humidity Forecast (24h)
        </h3>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" vertical={false} />
              <XAxis dataKey="time" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} tickLine={false} axisLine={false} dy={10} />
              <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} tickLine={false} axisLine={false} dx={-10} />
              <Tooltip 
                contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: '#f8fafc', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)' }}
                itemStyle={{ color: '#f8fafc', fontWeight: 500 }}
              />
              <Legend wrapperStyle={{ paddingTop: '20px' }} iconType="circle" />
              <Line type="monotone" dataKey="API Humidity" name="Open-Meteo" stroke="#06b6d4" strokeWidth={3} dot={false} activeDot={{ r: 6, strokeWidth: 0, fill: '#06b6d4' }} />
              <Line type="monotone" dataKey="LSTM Humidity" name="LSTM Model" stroke="#ec4899" strokeWidth={3} dot={false} strokeDasharray="5 5" activeDot={{ r: 6, strokeWidth: 0, fill: '#ec4899' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default ForecastCharts;
