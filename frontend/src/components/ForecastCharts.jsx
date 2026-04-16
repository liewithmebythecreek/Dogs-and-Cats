/**
 * ForecastCharts.jsx
 * Full-width single-variable AreaChart — the "weather map" equivalent.
 * Shows all 48h of the selected variable; a ReferenceLine moves with playback.
 */
import React, { useMemo } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  ReferenceLine, ResponsiveContainer, Tooltip,
} from 'recharts'
import { VARIABLES } from './ControlPanel'

/* Custom tooltip styled to match the dark theme */
const CustomTooltip = ({ active, payload, label, unit, color }) => {
  if (!active || !payload?.length) return null
  return (
    <div
      className="rounded-lg px-3 py-2 text-xs shadow-2xl border"
      style={{ background: '#0d1117', borderColor: `${color}40` }}
    >
      <p className="text-slate-400 mb-1">{label}</p>
      <p className="font-bold" style={{ color }}>
        {Number(payload[0].value).toFixed(1)} {unit}
      </p>
    </div>
  )
}

/* Mini stat pill shown in the top-right corner of the chart */
const StatPill = ({ label, value, color }) => (
  <div
    className="flex flex-col items-center px-3 py-1.5 rounded-lg border"
    style={{ background: `${color}12`, borderColor: `${color}30` }}
  >
    <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
    <span className="text-sm font-bold tabular-nums" style={{ color }}>{value}</span>
  </div>
)

export default function ForecastChart({ forecastSteps = [], selectedVar, currentStep }) {
  const varMeta = VARIABLES.find(v => v.key === selectedVar) ?? VARIABLES[0]

  /* Build recharts data array */
  const data = useMemo(() =>
    forecastSteps.map(s => ({
      label:  `+${s.hour}h`,
      value:  s[selectedVar],
      hour:   s.hour,
    })), [forecastSteps, selectedVar])

  /* Stats */
  const values    = data.map(d => d.value).filter(Boolean)
  const valMin    = values.length ? Math.min(...values).toFixed(1) : '—'
  const valMax    = values.length ? Math.max(...values).toFixed(1) : '—'
  const valCurrent= data[currentStep]?.value?.toFixed(1) ?? '—'

  const color = varMeta.color

  if (!forecastSteps.length) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 text-slate-600">
        <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center">
          <varMeta.icon className="w-6 h-6" />
        </div>
        <p className="text-sm">No forecast data — model may be loading</p>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 px-4 pt-3 pb-2">
      {/* ── Chart header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div className="flex items-center gap-3">
          <div
            className="w-1 self-stretch rounded-full"
            style={{ background: `linear-gradient(to bottom, ${color}, ${color}44)` }}
          />
          <div>
            <h2 className="text-white font-semibold text-sm leading-none">
              {varMeta.label}
              <span className="text-slate-500 font-normal text-xs ml-2">48-hour forecast</span>
            </h2>
            <p className="text-slate-600 text-[11px] mt-1">
              Graph-LSTM · {varMeta.unit} · 1h resolution
            </p>
          </div>
        </div>
        {/* Stat pills */}
        <div className="flex gap-2">
          <StatPill label="Current" value={`${valCurrent} ${varMeta.unit}`} color={color} />
          <StatPill label="Min"     value={`${valMin} ${varMeta.unit}`}    color="#64748b" />
          <StatPill label="Max"     value={`${valMax} ${varMeta.unit}`}    color="#94a3b8" />
        </div>
      </div>

      {/* ── Area chart ────────────────────────────────────────────────── */}
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 24, bottom: 4, left: 0 }}>
            <defs>
              <linearGradient id={`grad-${selectedVar}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor={color} stopOpacity={0.35} />
                <stop offset="75%"  stopColor={color} stopOpacity={0.05} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#ffffff09"
              vertical={false}
            />

            <XAxis
              dataKey="label"
              stroke="transparent"
              tick={{ fill: '#475569', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              interval={5}
              dy={6}
            />
            <YAxis
              stroke="transparent"
              tick={{ fill: '#475569', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              dx={-4}
              width={40}
            />

            <Tooltip
              content={<CustomTooltip unit={varMeta.unit} color={color} />}
              cursor={{ stroke: `${color}50`, strokeWidth: 1, strokeDasharray: '4 2' }}
            />

            {/* Moving reference line = current playback step */}
            {data[currentStep] && (
              <ReferenceLine
                x={data[currentStep].label}
                stroke={color}
                strokeWidth={1.5}
                strokeDasharray="0"
                label={{
                  value: `▼ T+${currentStep+1}h`,
                  position: 'top',
                  fill: color,
                  fontSize: 10,
                  fontWeight: 700,
                }}
              />
            )}

            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              fill={`url(#grad-${selectedVar})`}
              dot={false}
              activeDot={{ r: 5, fill: color, strokeWidth: 0, style: { filter: `drop-shadow(0 0 4px ${color})` } }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
