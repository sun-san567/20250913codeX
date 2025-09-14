import React from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  LineElement,
  LinearScale,
  PointElement,
  TimeScale,
  Legend,
  Tooltip,
} from 'chart.js'
import 'chartjs-adapter-date-fns'

ChartJS.register(LineElement, LinearScale, PointElement, TimeScale, Legend, Tooltip)

type Props = {
  data: { date: string; weight: number }[]
  ma7?: number[]
  goal?: number | null
  dark?: boolean
}

export function WeightChart({ data, ma7, goal, dark }: Props) {
  const dates = data.map((d) => d.date)
  const dsWeight = data.map((d) => d.weight)
  const color = dark ? '#4DD0E1' : '#4C7AF2'
  const maColor = dark ? '#FF6692' : '#EF553B'
  const goalColor = dark ? '#B6E880' : '#00CC96'

  return (
    <Line
      data={{
        labels: dates,
        datasets: [
          { label: '体重', data: dsWeight, borderColor: color, backgroundColor: color, tension: 0.25, pointRadius: 2 },
          ma7 ? { label: '7日平均', data: ma7, borderColor: maColor, backgroundColor: maColor, tension: 0.25, pointRadius: 0 } : undefined,
          goal != null
            ? { label: '目標', data: dates.map(() => goal), borderColor: goalColor, borderDash: [6, 6], pointRadius: 0 }
            : undefined,
        ].filter(Boolean) as any,
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom' as const, labels: { color: dark ? '#FFFFFF' : '#2e3a59' } } },
        scales: {
          x: { type: 'time', time: { unit: 'day', tooltipFormat: 'yyyy-MM-dd' }, grid: { color: dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)' }, ticks: { color: dark ? '#FFFFFF' : '#2e3a59' } },
          y: { ticks: { callback: (v) => `${v} kg`, color: dark ? '#FFFFFF' : '#2e3a59' }, grid: { color: dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)' } },
        },
      }}
      height={320}
    />
  )
}
