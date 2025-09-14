import React, { useEffect, useMemo, useState } from 'react'
import { RangeSegment } from './components/RangeSegment'
import { WeightChart } from './components/WeightChart'
import { ExerciseStackedBar } from './components/ExerciseStackedBar'
import type { RangeKey, Weight } from './api/types'
import { getWeights, getGoalWeight, getExercisesByActivity } from './api/client'

export default function App() {
  const [dark, setDark] = useState<boolean>(false)
  const [range, setRange] = useState<RangeKey>('7d')
  const [weights, setWeights] = useState<Weight[]>([])
  const [goal, setGoal] = useState<number | null>(null)
  const [byAct, setByAct] = useState<{ date: string; activity: string; duration_min: number }[]>([])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  useEffect(() => {
    ;(async () => {
      const [w, g, ex] = await Promise.all([getWeights(range), getGoalWeight(), getExercisesByActivity(range)])
      setWeights(w)
      setGoal(g)
      setByAct(ex)
    })().catch(console.error)
  }, [range])

  const ma7 = useMemo(() => {
    const xs = weights.map((w) => w.weight)
    const out: number[] = []
    for (let i = 0; i < xs.length; i++) {
      const s = Math.max(0, i - 6)
      const seg = xs.slice(s, i + 1)
      const avg = seg.reduce((a, b) => a + b, 0) / seg.length
      out.push(parseFloat(avg.toFixed(1)))
    }
    return out
  }, [weights])

  const stacked = useMemo(() => {
    const dates = Array.from(new Set(byAct.map((r) => r.date))).sort()
    const acts = Array.from(new Set(byAct.map((r) => r.activity))).sort()
    const stacks: Record<string, number[]> = {}
    acts.forEach((a) => (stacks[a] = Array(dates.length).fill(0)))
    byAct.forEach((r) => {
      const di = dates.indexOf(r.date)
      if (di >= 0) stacks[r.activity][di] = r.duration_min
    })
    return { dates, stacks }
  }, [byAct])

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between p-4">
        <h1 className="text-xl font-semibold">体重・運動トラッカー（Web）</h1>
        <div className="flex items-center gap-3">
          <RangeSegment value={range} onChange={setRange} />
          <button className="btn btn-muted" onClick={() => setDark((d) => !d)}>{dark ? '🌙' : '🌞'}</button>
        </div>
      </header>

      <main className="p-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <section className="card p-4 h-[420px]">
          <h2 className="mb-2 font-medium">📉 体重推移</h2>
          <div className="h-[360px]">
            <WeightChart data={weights} ma7={ma7} goal={goal} dark={dark} />
          </div>
        </section>
        <section className="card p-4 h-[420px]">
          <h2 className="mb-2 font-medium">🏃‍♂️ 種目別（積み上げ）</h2>
          <div className="h-[360px]">
            <ExerciseStackedBar dates={stacked.dates} stacks={stacked.stacks} dark={dark} />
          </div>
        </section>
        <section>
          <KanbanBoard />
        </section>
      </main>

      <footer className="p-4 text-xs opacity-70">API: {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}</footer>
    </div>
  )
}
