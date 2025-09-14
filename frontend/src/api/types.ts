export type RangeKey = '7d' | '30d' | '90d' | '180d' | '365d' | 'all'

export type Weight = { date: string; weight: number }
export type WeightStats = { avg: number | null; delta: number | null; min: number | null; max: number | null }

export type Exercise = { id?: number; date: string; activity: string; duration_min: number }
export type DailyExercise = { date: string; total_min: number }

