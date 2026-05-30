'use client'

import { useMemo } from 'react'

export interface TrendPoint {
  date: string
  count: number
}

interface TrendChartProps {
  data: TrendPoint[]
  color?: string
  height?: number
  ariaLabel?: string
}

/**
 * Minimal SVG sparkline + bar chart. No external deps, no animation, no axes.
 * Intentional: keeps the bundle tiny and renders the trend at a glance. If we
 * need axes / tooltips later, swap this for Recharts in one place.
 */
export function TrendChart({
  data,
  color = 'hsl(var(--primary))',
  height = 60,
  ariaLabel,
}: TrendChartProps) {
  const { path, areaPath, points, total } = useMemo(() => {
    if (data.length === 0) {
      return { path: '', areaPath: '', points: [] as { x: number; y: number }[], total: 0 }
    }
    const max = Math.max(1, ...data.map(d => d.count))
    const total = data.reduce((acc, d) => acc + d.count, 0)
    const w = 100
    const h = 100
    const step = data.length > 1 ? w / (data.length - 1) : 0
    const pts = data.map((d, i) => ({
      x: data.length === 1 ? w / 2 : i * step,
      y: h - (d.count / max) * h * 0.9 - 5,
    }))
    const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
    const area = `${line} L ${pts[pts.length - 1].x} ${h} L ${pts[0].x} ${h} Z`
    return { path: line, areaPath: area, points: pts, total }
  }, [data])

  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-xs text-muted-foreground"
        style={{ height }}
      >
        No activity yet
      </div>
    )
  }

  const startLabel = data[0]?.date
  const endLabel = data[data.length - 1]?.date

  return (
    <div className="flex flex-col gap-1">
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        role="img"
        aria-label={ariaLabel ?? `Trend over ${data.length} days, total ${total}`}
        style={{ height, width: '100%' }}
      >
        <path d={areaPath} fill={color} opacity={0.12} />
        <path d={path} fill="none" stroke={color} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
        {points.length > 0 && (
          <circle
            cx={points[points.length - 1].x}
            cy={points[points.length - 1].y}
            r={1.5}
            fill={color}
            vectorEffect="non-scaling-stroke"
          />
        )}
      </svg>
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>{startLabel}</span>
        <span className="font-medium text-foreground">total {total}</span>
        <span>{endLabel}</span>
      </div>
    </div>
  )
}
