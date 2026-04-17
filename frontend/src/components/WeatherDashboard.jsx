/**
 * WeatherDashboard.jsx
 * ECMWF-inspired layout:
 *   [dark navbar]
 *   [ControlPanel sidebar | main chart area]
 *                          [PlaybackBar]
 *   [metadata strip]
 */
import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  Loader2, RefreshCw, Network, WifiOff, Info,
} from 'lucide-react'
import { getCurrentConditions, getGraphForecast, CITY_NAMES } from '../services/api'
import ControlPanel, { VARIABLES } from './ControlPanel'
import ForecastChart  from './ForecastCharts'
import PlaybackBar    from './PlaybackBar'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Separator } from '@/components/ui/separator'

const TOTAL_STEPS = 48

export default function WeatherDashboard() {
  // ── Data state ──────────────────────────────────────────────────────────────
  const [currentData,  setCurrentData]  = useState(null)
  const [forecastData, setForecastData] = useState(null)
  const [loading,      setLoading]      = useState(false)
  const [error,        setError]        = useState(null)
  const [lastUpdated,  setLastUpdated]  = useState(null)
  const [modelReady,   setModelReady]   = useState(false)

  // ── UI state ─────────────────────────────────────────────────────────────────
  const [selectedCity, setSelectedCity] = useState(CITY_NAMES[0])
  const [selectedVar,  setSelectedVar]  = useState('temperature_2m')
  const [currentStep,  setCurrentStep]  = useState(0)
  const [isPlaying,    setIsPlaying]    = useState(false)
  const [loop,         setLoop]         = useState(true)
  const [speed,        setSpeed]        = useState(600)  // ms per frame
  const [forecastSource, setForecastSource] = useState('openmeteo') // 'openmeteo' | 'model'

  const playRef = useRef(null)

  // ── Fetch ────────────────────────────────────────────────────────────────────
  const fetchAll = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const [current, graph] = await Promise.all([
        getCurrentConditions(),
        getGraphForecast(),
      ])
      setCurrentData(current)
      setForecastData(graph)
      // Chart uses Open-Meteo native forecast; model forecast kept for reference
      setModelReady(!!(graph?.forecast && Object.keys(graph.forecast).length > 0))
      setLastUpdated(new Date().toLocaleTimeString())
      setCurrentStep(0)
    } catch (err) {
      console.error('[WeatherDashboard]', err)
      setError(err.message ?? 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  // ── Playback timer ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (playRef.current) clearInterval(playRef.current)
    if (!isPlaying) return

    playRef.current = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= TOTAL_STEPS - 1) {
          if (loop) return 0
          setIsPlaying(false)
          return prev
        }
        return prev + 1
      })
    }, speed)
    return () => clearInterval(playRef.current)
  }, [isPlaying, loop, speed])

  // ── Derived ──────────────────────────────────────────────────────────────────
  const cityForecast = forecastSource === 'openmeteo'
    ? forecastData?.openmeteo_forecast?.[selectedCity] ?? []
    : forecastData?.forecast?.[selectedCity] ?? []
  const forecastDate = (() => {
    const d = new Date()
    d.setMinutes(0, 0, 0)
    d.setHours(d.getHours() + currentStep)
    return d.toLocaleString('en-GB', {
      weekday: 'short', day: '2-digit', month: 'short',
      year: 'numeric', hour: '2-digit', minute: '2-digit',
    }) + ' UTC'
  })()

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="h-full flex flex-col" style={{ background: '#0b0f1a' }}>

      {/* ═══════════════════════════════════════════════════════════════════════
          NAVBAR  (ECMWF dark bar)
      ════════════════════════════════════════════════════════════════════════ */}
      <nav
        className="shrink-0 flex items-center px-4 gap-4 border-b border-white/10 z-10"
        style={{ height: 'var(--navbar-h)', background: '#060a14' }}
      >
        {/* Brand */}
        <div className="flex items-center gap-2 mr-2">
          <div className="w-7 h-7 rounded-md bg-orange-500/20 border border-orange-500/30
                          flex items-center justify-center">
            <Network className="w-4 h-4 text-orange-400" />
          </div>
          <span className="font-bold text-white tracking-tight text-sm">NeuralWeather</span>
          <span className="hidden sm:block text-slate-600 text-sm">|</span>
          <span className="hidden sm:block text-slate-500 text-xs">GraphCast-style ML Forecast</span>
          
          {/* Source Toggle */}
          <div className="hidden md:flex items-center ml-2 bg-[#0d1320] rounded-full p-0.5 border border-white/5">
            <button
              onClick={() => setForecastSource('openmeteo')}
              className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold tracking-wide transition-colors ${
                forecastSource === 'openmeteo' 
                  ? 'bg-sky-500/20 text-sky-400' 
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              Open-Meteo
            </button>
            <button
              onClick={() => setForecastSource('model')}
              className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold tracking-wide transition-colors ${
                forecastSource === 'model' 
                  ? 'bg-orange-500/20 text-orange-400' 
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              Model
            </button>
          </div>
        </div>

        <Separator orientation="vertical" className="h-5 bg-white/10" />

        {/* Breadcrumb-style product label */}
        <div className="hidden md:flex items-center gap-2 flex-1">
          <span className="text-orange-400 text-xs font-semibold tracking-wide">
            EXPERIMENTAL
          </span>
          <span className="text-slate-600 text-xs">·</span>
          <span className="text-slate-400 text-xs">
            Graph-LSTM · Mean Sea-Level Pressure & Multi-Var · 48 h Punjab Region
          </span>
        </div>

        {/* Right controls */}
        <div className="ml-auto flex items-center gap-2">
          {/* Live indicator */}
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="text-emerald-500 text-[11px] font-medium hidden sm:block">LIVE</span>
          </div>

          {lastUpdated && (
            <span className="text-slate-600 text-[11px] hidden md:block">
              Updated {lastUpdated}
            </span>
          )}

          {/* Refresh */}
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={fetchAll}
                disabled={loading}
                className="pb-btn"
                aria-label="Refresh data"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-orange-400' : ''}`} />
              </button>
            </TooltipTrigger>
            <TooltipContent className="text-xs bg-[#0d1117] border-white/10">
              Refresh data
            </TooltipContent>
          </Tooltip>
        </div>
      </nav>

      {/* Error banner */}
      {error && (
        <div className="shrink-0 flex items-center gap-2 px-4 py-2 bg-red-950/50
                        border-b border-red-900/50 text-red-400 text-xs">
          <WifiOff className="w-3.5 h-3.5 shrink-0" />
          {error}
          <button onClick={fetchAll} className="ml-2 underline hover:text-red-200">
            Retry
          </button>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          MAIN BODY  sidebar + chart
      ════════════════════════════════════════════════════════════════════════ */}
      <div className="flex flex-1 min-h-0">

        {/* LEFT SIDEBAR */}
        <ControlPanel
          cities={CITY_NAMES}
          selectedCity={selectedCity}
          onCityChange={setSelectedCity}
          selectedVar={selectedVar}
          onVarChange={v => { setSelectedVar(v); setCurrentStep(0); setIsPlaying(false) }}
          currentStep={currentStep}
          totalSteps={TOTAL_STEPS}
          currentConditions={currentData}
          modelReady={modelReady}
        />

        {/* RIGHT — chart + playback bar */}
        <div className="flex-1 flex flex-col min-w-0">

          {/* ── Page title strip (ECMWF breadcrumb style) ─────────────── */}
          <div className="shrink-0 px-5 py-2.5 border-b border-white/10
                          flex items-center justify-between"
               style={{ background: '#0d1320' }}>
            <div>
              <h1 className="text-white text-sm font-semibold leading-none">
                {VARIABLES.find(v => v.key === selectedVar)?.label ?? 'Forecast'}
                <span className="text-slate-500 font-normal ml-2 text-xs">
                  · {selectedCity}, {
                    { Ropar:'Punjab', Chandigarh:'UT', Ludhiana:'Punjab',
                      Patiala:'Punjab', Jalandhar:'Punjab',
                      Ambala:'Haryana', Shimla:'H.P.' }[selectedCity]
                  }
                </span>
              </h1>
              <p className="text-slate-600 text-[11px] mt-0.5">
                {forecastSource === 'openmeteo' 
                  ? 'Open-Meteo · 48-h native forecast'
                  : 'Machine learning · STGNN inference'}
              </p>
            </div>

            {/* SELECT DIMENSIONS hint */}
            <div className="flex items-center gap-2 text-orange-400 text-[11px] font-bold
                            tracking-widest uppercase cursor-default">
              <Info className="w-3.5 h-3.5" />
              <span className="hidden md:block">Select Dimensions</span>
            </div>
          </div>

          {/* ── Loading overlay ─────────────────────────────────────────── */}
          {loading && !forecastData && (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 text-slate-600">
              <Loader2 className="w-10 h-10 animate-spin text-orange-500/50" />
              <p className="text-sm">Fetching 7-node graph data…</p>
            </div>
          )}

          {/* ── Main chart ──────────────────────────────────────────────── */}
          {(forecastData || !loading) && (
            <ForecastChart
              forecastSteps={cityForecast}
              selectedVar={selectedVar}
              currentStep={currentStep}
            />
          )}

          {/* ── Playback bar ────────────────────────────────────────────── */}
          <PlaybackBar
            currentStep={currentStep}
            totalSteps={TOTAL_STEPS}
            isPlaying={isPlaying}
            onPlayPause={() => setIsPlaying(p => !p)}
            onFirst={() => { setCurrentStep(0);               setIsPlaying(false) }}
            onLast ={() => { setCurrentStep(TOTAL_STEPS - 1); setIsPlaying(false) }}
            onPrev ={() => setCurrentStep(p => Math.max(0, p - 1))}
            onNext ={() => setCurrentStep(p => Math.min(TOTAL_STEPS - 1, p + 1))}
            onScrub={v  => { setCurrentStep(v); setIsPlaying(false) }}
            loop={loop}
            onToggleLoop={() => setLoop(l => !l)}
            speed={speed}
            onSpeedChange={setSpeed}
            forecastDate={forecastDate}
          />
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          METADATA STRIP  (ECMWF model info row at bottom)
      ════════════════════════════════════════════════════════════════════════ */}
      <footer
        className="shrink-0 flex flex-wrap items-center gap-x-6 gap-y-1
                   px-5 py-2 border-t border-white/10 text-[11px] text-slate-600"
        style={{ background: '#060a14' }}
      >
        <span><b className="text-slate-500">Model</b> &nbsp;Graph-LSTM, Punjab Region</span>
        <span><b className="text-slate-500">Training data</b> &nbsp;Open-Meteo (ERA5-equivalent)</span>
        <span><b className="text-slate-500">Initial conditions</b> &nbsp;Open-Meteo live analysis</span>
        <span><b className="text-slate-500">Resolution</b> &nbsp;1 h · 7 nodes · 48 h horizon</span>
        <span><b className="text-slate-500">Region</b> &nbsp;Punjab / Himachal Pradesh / Haryana</span>
        <span className="ml-auto text-slate-700">
          NeuralWeather · CC BY-NC-SA 4.0 inspired by ECMWF Charts
        </span>
      </footer>
    </div>
  )
}
