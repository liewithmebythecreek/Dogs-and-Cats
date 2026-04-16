/**
 * PlaybackBar.jsx
 * ECMWF-style dark animation control bar at the bottom of the chart.
 * Controls: |◀  ◀  ▶/⏸  ▶  ▶|  plus a scrubber slider
 */
import React from 'react'
import {
  SkipBack, ChevronLeft, Play, Pause, ChevronRight, SkipForward,
  Repeat2, Gauge,
} from 'lucide-react'
import { Slider } from '@/components/ui/slider'
import {
  Tooltip, TooltipContent, TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

const SPEEDS = [
  { label: '0.5×', ms: 1200 },
  { label: '1×',   ms:  600 },
  { label: '2×',   ms:  300 },
  { label: '4×',   ms:  150 },
]

function PbBtn({ onClick, disabled, tip, children, primary }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={onClick}
          disabled={disabled}
          className={primary ? 'pb-btn-primary' : 'pb-btn'}
        >
          {children}
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="text-xs bg-[#0d1117] border-white/10 text-slate-300">
        {tip}
      </TooltipContent>
    </Tooltip>
  )
}

export default function PlaybackBar({
  currentStep, totalSteps,
  isPlaying, onPlayPause,
  onFirst, onLast, onPrev, onNext,
  onScrub,
  loop, onToggleLoop,
  speed, onSpeedChange,
  forecastDate,
}) {
  const pct = totalSteps > 1 ? Math.round((currentStep / (totalSteps - 1)) * 100) : 0

  return (
    <div
      className="shrink-0 flex flex-col"
      style={{ height: 'var(--playbar-h)', background: '#111827' }}
    >
      {/* ── Orange scrubber slider ───────────────────────────────────── */}
      <div className="px-4 pt-2">
        <Slider
          id="playback-slider"
          min={0}
          max={totalSteps - 1}
          step={1}
          value={[currentStep]}
          onValueChange={([v]) => onScrub(v)}
          className="[&>span:first-child]:h-1 [&>span:first-child]:bg-white/10
                     [&_[role=slider]]:h-3 [&_[role=slider]]:w-3
                     [&_[role=slider]]:bg-orange-400 [&_[role=slider]]:border-0
                     [&_[role=slider]]:shadow-[0_0_6px_rgba(249,115,22,0.7)]
                     [&>span:first-child>span]:bg-orange-500"
        />
      </div>

      {/* ── Controls row ────────────────────────────────────────────── */}
      <div className="flex-1 flex items-center px-3 gap-1">
        {/* Media buttons */}
        <div className="flex items-center gap-0.5">
          <PbBtn onClick={onFirst} disabled={currentStep === 0}              tip="First frame">
            <SkipBack className="w-4 h-4" />
          </PbBtn>
          <PbBtn onClick={onPrev}  disabled={currentStep === 0}              tip="Step back">
            <ChevronLeft className="w-4 h-4" />
          </PbBtn>
          <PbBtn onClick={onPlayPause} primary tip={isPlaying ? 'Pause' : 'Play'}>
            {isPlaying
              ? <Pause className="w-4 h-4" />
              : <Play  className="w-4 h-4" />}
          </PbBtn>
          <PbBtn onClick={onNext}  disabled={currentStep === totalSteps - 1} tip="Step forward">
            <ChevronRight className="w-4 h-4" />
          </PbBtn>
          <PbBtn onClick={onLast}  disabled={currentStep === totalSteps - 1} tip="Last frame">
            <SkipForward className="w-4 h-4" />
          </PbBtn>
        </div>

        {/* Timestamp */}
        <div className="flex-1 flex items-center justify-center gap-3 tabular-nums">
          <span className="text-slate-400 text-[11px]">{forecastDate}</span>
          <span className="px-2 py-0.5 rounded bg-orange-500/15 text-orange-400
                           text-xs font-bold border border-orange-500/25">
            T +{currentStep}h
          </span>
          <span className="text-slate-600 text-[11px]">{pct}%</span>
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-1">
          {/* Speed select */}
          <Select value={String(speed)} onValueChange={v => onSpeedChange(Number(v))}>
            <SelectTrigger
              className="h-7 w-16 text-[11px] bg-white/5 border-white/10
                         text-slate-300 focus:ring-orange-500/30 px-2 py-0"
            >
              <Gauge className="w-3 h-3 mr-1 text-slate-500" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#1e2540] border-white/10 text-slate-200 text-xs">
              {SPEEDS.map(s => (
                <SelectItem key={s.ms} value={String(s.ms)} className="focus:bg-orange-500/20">
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Loop toggle */}
          <PbBtn onClick={onToggleLoop} tip={loop ? 'Loop on' : 'Loop off'}>
            <Repeat2 className={`w-4 h-4 ${loop ? 'text-orange-400' : ''}`} />
          </PbBtn>
        </div>
      </div>
    </div>
  )
}
