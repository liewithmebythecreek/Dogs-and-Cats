import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from '@/components/ui/chart';

// ── Chart colour configs ───────────────────────────────────────────────────────
const configTemp = {
  temperature_2m: { label: 'Temperature (°C)', color: '#f59e0b' },
};
const configHumidity = {
  relative_humidity_2m: { label: 'Humidity (%)', color: '#06b6d4' },
};
const configWind = {
  wind_speed_10m: { label: 'Wind (km/h)', color: '#a78bfa' },
};
const configPrecip = {
  precipitation: { label: 'Precip. (mm)', color: '#34d399' },
};

// ── Helper: build tick labels (h+1, h+6, h+12 …) ─────────────────────────────
function buildChartData(forecastSteps) {
  return forecastSteps.map((step, idx) => ({
    label: `+${step.hour}h`,
    temperature_2m:       step.temperature_2m,
    relative_humidity_2m: step.relative_humidity_2m,
    wind_speed_10m:       step.wind_speed_10m,
    precipitation:        step.precipitation,
  }));
}

// ── Shared mini-chart card ─────────────────────────────────────────────────────
function MetricChart({ title, dotColor, config, dataKey, data, unit = '' }) {
  return (
    <Card className="bg-slate-900/50 border-white/5 backdrop-blur-md transition-all">
      <CardHeader className="pb-2">
        <CardTitle
          className="text-lg font-semibold flex items-center gap-2"
          style={{ fontFamily: 'Outfit, sans-serif', color: '#e2e8f0' }}
        >
          <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: dotColor }} />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[240px] w-full">
          <ChartContainer config={config} className="w-full h-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 5, right: 16, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff12" vertical={false} />
                <XAxis
                  dataKey="label"
                  stroke="#94a3b8"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  interval={5}
                  dy={8}
                />
                <YAxis
                  stroke="#94a3b8"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  dx={-6}
                />
                <ChartTooltip
                  content={<ChartTooltipContent />}
                  formatter={(v) => [`${v} ${unit}`, '']}
                />
                <ChartLegend
                  content={<ChartLegendContent />}
                  wrapperStyle={{ paddingTop: '12px' }}
                />
                <Line
                  type="monotone"
                  dataKey={dataKey}
                  stroke={dotColor}
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 5, strokeWidth: 0 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────
const ForecastCharts = ({ forecastSteps = [], cityName }) => {
  if (!forecastSteps || forecastSteps.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-500">
        {cityName
          ? `No forecast data available for ${cityName}.`
          : 'Select a city to view the 48-hour forecast.'}
      </div>
    );
  }

  const data = buildChartData(forecastSteps);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full mt-2">
      <MetricChart
        title="Temperature · 48 h"
        dotColor="#f59e0b"
        config={configTemp}
        dataKey="temperature_2m"
        data={data}
        unit="°C"
      />
      <MetricChart
        title="Humidity · 48 h"
        dotColor="#06b6d4"
        config={configHumidity}
        dataKey="relative_humidity_2m"
        data={data}
        unit="%"
      />
      <MetricChart
        title="Wind Speed · 48 h"
        dotColor="#a78bfa"
        config={configWind}
        dataKey="wind_speed_10m"
        data={data}
        unit="km/h"
      />
      <MetricChart
        title="Precipitation · 48 h"
        dotColor="#34d399"
        config={configPrecip}
        dataKey="precipitation"
        data={data}
        unit="mm"
      />
    </div>
  );
};

export default ForecastCharts;
