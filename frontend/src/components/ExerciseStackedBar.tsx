import React from 'react'
import { Chart as ChartJS, BarElement, CategoryScale, LinearScale, Tooltip, Legend } from 'chart.js'
import { Bar } from 'react-chartjs-2'

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend)

type Series = { date: string; [activity: string]: any }

export function ExerciseStackedBar({
  dates,
  stacks,
  dark,
}: {
  dates: string[]
  stacks: Record<string, number[]> // activity -> values (aligned with dates)
  dark?: boolean
}) {
  const colorPalette = ['#636EFA', '#EF553B', '#00CC96', '#FFA15A', '#19D3F3', '#B6E880', '#FF6692']
  const datasets = Object.entries(stacks).map(([name, values], i) => ({
    label: name,
    data: values,
    backgroundColor: colorPalette[i % colorPalette.length],
    borderWidth: 0,
  }))
  return (
    <Bar
      data={{ labels: dates, datasets }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom' as const, labels: { color: dark ? '#FFFFFF' : '#2e3a59' } } },
        scales: {
          x: { stacked: true, grid: { color: dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)' }, ticks: { color: dark ? '#FFFFFF' : '#2e3a59' } },
          y: { stacked: true, ticks: { callback: (v) => `${v} 分`, color: dark ? '#FFFFFF' : '#2e3a59' }, grid: { color: dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)' } },
        },
      }}
      height={320}
    />
  )
}
