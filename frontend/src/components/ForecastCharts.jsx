import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent
} from "@/components/ui/chart";

const chartConfigTemp = {
  apiTemp: {
    label: "Open-Meteo",
    color: "#3b82f6",
  },
  lstmTemp: {
    label: "LSTM Model",
    color: "#f59e0b",
  },
};

const chartConfigHumidity = {
  apiHumidity: {
    label: "Open-Meteo",
    color: "#06b6d4",
  },
  lstmHumidity: {
    label: "LSTM Model",
    color: "#ec4899",
  },
};

const ForecastCharts = ({ forecast, mlPredictions }) => {
  if (!forecast || !forecast.hourly) return null;

  const chartData = [];
  const limit = 24; // Show next 24 hours

  for (let i = 0; i < limit; i++) {
    const timeFull = new Date(forecast.hourly.time[i]);
    const label = timeFull.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    chartData.push({
      time: label,
      apiTemp: forecast.hourly.temperature_2m[i],
      lstmTemp: mlPredictions && mlPredictions.length > i ? mlPredictions[i].temperature_2m : null,
      apiHumidity: forecast.hourly.relative_humidity_2m[i],
      lstmHumidity: mlPredictions && mlPredictions.length > i ? mlPredictions[i].relative_humidity_2m : null,
    });
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 w-full mt-4">
      {/* Temperature Chart */}
      <Card className="bg-slate-900/50 border-white/5 backdrop-blur-md relative group transition-all">
        <CardHeader className="pb-2">
          <CardTitle className="text-xl font-semibold bg-clip-text text-transparent bg-gradient-to-r from-orange-200 to-red-200 flex items-center gap-2" style={{fontFamily: 'Outfit, sans-serif'}}>
             <div className="w-2 h-2 rounded-full bg-orange-400 animate-pulse"></div>
             Temperature Forecast (24h)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] w-full">
            <ChartContainer config={chartConfigTemp} className="w-full h-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" vertical={false} />
                  <XAxis dataKey="time" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} tickLine={false} axisLine={false} dy={10} />
                  <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} tickLine={false} axisLine={false} dx={-10} />
                  <ChartTooltip 
                    content={<ChartTooltipContent />}
                  />
                  <ChartLegend content={<ChartLegendContent />} wrapperStyle={{ paddingTop: '20px' }} />
                  <Line type="monotone" dataKey="apiTemp" stroke="var(--color-apiTemp)" strokeWidth={3} dot={false} activeDot={{ r: 6, strokeWidth: 0 }} />
                  <Line type="monotone" dataKey="lstmTemp" stroke="var(--color-lstmTemp)" strokeWidth={3} dot={false} strokeDasharray="5 5" activeDot={{ r: 6, strokeWidth: 0 }} />
                </LineChart>
              </ResponsiveContainer>
            </ChartContainer>
          </div>
        </CardContent>
      </Card>

      {/* Humidity Chart */}
      <Card className="bg-slate-900/50 border-white/5 backdrop-blur-md relative group transition-all">
        <CardHeader className="pb-2">
          <CardTitle className="text-xl font-semibold bg-clip-text text-transparent bg-gradient-to-r from-cyan-200 to-blue-200 flex items-center gap-2" style={{fontFamily: 'Outfit, sans-serif'}}>
             <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></div>
             Humidity Forecast (24h)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] w-full">
            <ChartContainer config={chartConfigHumidity} className="w-full h-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" vertical={false} />
                  <XAxis dataKey="time" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} tickLine={false} axisLine={false} dy={10} />
                  <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} tickLine={false} axisLine={false} dx={-10} />
                  <ChartTooltip 
                    content={<ChartTooltipContent />}
                  />
                  <ChartLegend content={<ChartLegendContent />} wrapperStyle={{ paddingTop: '20px' }} />
                  <Line type="monotone" dataKey="apiHumidity" stroke="var(--color-apiHumidity)" strokeWidth={3} dot={false} activeDot={{ r: 6, strokeWidth: 0 }} />
                  <Line type="monotone" dataKey="lstmHumidity" stroke="var(--color-lstmHumidity)" strokeWidth={3} dot={false} strokeDasharray="5 5" activeDot={{ r: 6, strokeWidth: 0 }} />
                </LineChart>
              </ResponsiveContainer>
            </ChartContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ForecastCharts;
