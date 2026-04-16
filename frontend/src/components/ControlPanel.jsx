/**
 * ControlPanel.jsx
 * Left sidebar — "SELECT DIMENSIONS" ECMWF-style control panel
 */
import React from 'react'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import {
  Thermometer, Droplets, Wind, Gauge, CloudRain,
  Network, Activity, Layers3,
} from 'lucide-react'

export const VARIABLES = [
  { key: 'temperature_2m',       label: 'Temperature',  unit: '°C',  color: '#f97316', icon: Thermometer },
  { key: 'relative_humidity_2m', label: 'Humidity',     unit: '%',   color: '#06b6d4', icon: Droplets    },
  { key: 'wind_speed_10m',       label: 'Wind Speed',   unit: 'km/h',color: '#a78bfa', icon: Wind        },
  { key: 'surface_pressure',     label: 'Pressure',     unit: 'hPa', color: '#fb7185', icon: Gauge       },
  { key: 'precipitation',        label: 'Precipitation',unit: 'mm',  color: '#34d399', icon: CloudRain   },
]

export const CITY_META = {
  Ropar:      { region: 'Punjab'  },
  Chandigarh: { region: 'UT'     },
  Ludhiana:   { region: 'Punjab'  },
  Patiala:    { region: 'Punjab'  },
  Jalandhar:  { region: 'Punjab'  },
  Ambala:     { region: 'Haryana' },
  Shimla:     { region: 'H.P.'   },
}

const StatRow = ({ label, value, accent }) => (
  <div className="flex justify-between items-center py-1.5">
    <span className="text-slate-500 text-xs">{label}</span>
    <span className="text-xs font-semibold" style={{ color: accent ?? '#94a3b8' }}>{value}</span>
  </div>
)

export default function ControlPanel({
  cities, selectedCity, onCityChange,
  selectedVar, onVarChange,
  currentStep, totalSteps,
  currentConditions,
  modelReady,
}) {
  const varMeta   = VARIABLES.find(v => v.key === selectedVar) ?? VARIABLES[0]
  const VarIcon   = varMeta.icon
  const cityData  = currentConditions?.[selectedCity]

  return (
    <aside
      className="flex flex-col h-full ecmwf-surface border-r border-white/10 text-sm select-none"
      style={{ width: 'var(--sidebar-w)' }}
    >
      {/* ── Panel header ──────────────────────────────────────────────── */}
      <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between shrink-0">
        <span className="text-[11px] font-bold tracking-[0.15em] uppercase text-orange-400">
          Select Dimensions
        </span>
        <Layers3 className="w-3.5 h-3.5 text-slate-500" />
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">

        {/* ── City ──────────────────────────────────────────────────────── */}
        <div>
          <p className="dim-label">Location / Node</p>
          <Select value={selectedCity} onValueChange={onCityChange}>
            <SelectTrigger
              id="city-select"
              className="w-full bg-white/5 border-white/10 text-slate-200
                         focus:ring-orange-500/40 focus:border-orange-500/40 h-9 text-sm"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#1e2540] border-white/10 text-slate-200">
              {cities.map(city => (
                <SelectItem key={city} value={city} className="focus:bg-orange-500/20 focus:text-orange-100">
                  <span className="font-medium">{city}</span>
                  <span className="ml-2 text-slate-500 text-xs">{CITY_META[city]?.region}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* ── Variable ──────────────────────────────────────────────────── */}
        <div>
          <p className="dim-label">Forecast Variable</p>
          <Select value={selectedVar} onValueChange={onVarChange}>
            <SelectTrigger
              id="var-select"
              className="w-full bg-white/5 border-white/10 text-slate-200
                         focus:ring-orange-500/40 focus:border-orange-500/40 h-9 text-sm"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#1e2540] border-white/10 text-slate-200">
              {VARIABLES.map(v => {
                const Icon = v.icon
                return (
                  <SelectItem key={v.key} value={v.key} className="focus:bg-orange-500/20 focus:text-orange-100">
                    <span className="flex items-center gap-2">
                      <Icon className="w-3.5 h-3.5" style={{ color: v.color }} />
                      {v.label}
                      <span className="text-slate-500 text-xs">{v.unit}</span>
                    </span>
                  </SelectItem>
                )
              })}
            </SelectContent>
          </Select>

          {/* Variable colour swatch */}
          <div className="mt-2 flex items-center gap-2 px-2 py-1.5 rounded bg-white/5 border border-white/10">
            <span className="w-3 h-3 rounded-full shrink-0" style={{ background: varMeta.color }} />
            <span className="text-slate-300 text-xs flex-1">{varMeta.label}</span>
            <VarIcon className="w-3.5 h-3.5 text-slate-500" />
          </div>
        </div>

        <Separator className="bg-white/10" />

        {/* ── Current conditions ────────────────────────────────────────── */}
        <div>
          <p className="dim-label">Live Conditions · {selectedCity}</p>
          {cityData ? (
            <div className="rounded-lg bg-white/5 border border-white/10 px-3 divide-y divide-white/5">
              <StatRow label="Temperature" value={`${cityData.temperature_2m} °C`}   accent="#f97316" />
              <StatRow label="Humidity"    value={`${cityData.relative_humidity_2m} %`}  accent="#06b6d4" />
              <StatRow label="Wind"        value={`${cityData.wind_speed_10m} km/h`} accent="#a78bfa" />
              <StatRow label="Pressure"    value={`${cityData.surface_pressure} hPa`}accent="#fb7185" />
              <StatRow label="Precip."     value={`${cityData.precipitation} mm`}    accent="#34d399" />
            </div>
          ) : (
            <p className="text-slate-600 text-xs mt-1">Fetching data…</p>
          )}
        </div>

        <Separator className="bg-white/10" />

        {/* ── Model metadata ────────────────────────────────────────────── */}
        <div>
          <p className="dim-label">Model Info</p>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Model</span>
              <div className="flex items-center gap-1">
                <Network className="w-3 h-3 text-indigo-400" />
                <span className="text-indigo-300 font-semibold">Graph-LSTM</span>
              </div>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Nodes</span>
              <span className="text-slate-300 font-semibold">7 cities</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Horizon</span>
              <span className="text-slate-300 font-semibold">48 h</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Resolution</span>
              <span className="text-slate-300 font-semibold">1 h steps</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Region</span>
              <span className="text-slate-300 font-semibold">Punjab / N.India</span>
            </div>
            <div className="flex justify-between items-center pt-1">
              <span className="text-slate-500">ML Status</span>
              <Badge
                className="text-[10px] h-5 px-1.5"
                style={{
                  background: modelReady ? 'rgba(52,211,153,0.15)' : 'rgba(100,116,139,0.15)',
                  color:      modelReady ? '#34d399' : '#64748b',
                  border:     `1px solid ${modelReady ? '#34d39940' : '#64748b40'}`,
                }}
              >
                <Activity className="w-2.5 h-2.5 mr-1" />
                {modelReady ? 'Ready' : 'API-only'}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      {/* ── Step indicator (bottom of sidebar) ───────────────────────── */}
      <div className="shrink-0 border-t border-white/10 px-4 py-3">
        <div className="flex items-center justify-between">
          <span className="text-slate-500 text-xs">Forecast step</span>
          <span className="text-orange-400 font-bold text-sm tabular-nums">
            T+{currentStep}h
            <span className="text-slate-600 text-xs font-normal"> / {totalSteps}h</span>
          </span>
        </div>
        <div className="mt-2 h-1 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-orange-500 to-orange-400 transition-all"
            style={{ width: `${(currentStep / (totalSteps - 1)) * 100}%` }}
          />
        </div>
      </div>
    </aside>
  )
}
