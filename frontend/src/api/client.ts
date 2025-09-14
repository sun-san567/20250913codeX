import axios from 'axios'
import type { RangeKey, Weight, WeightStats, Exercise, DailyExercise } from './types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 10000,
})

export const getWeights = async (range: RangeKey) => {
  const { data } = await api.get<Weight[]>(`/weights`, { params: { range } })
  return data
}

export const getWeightStats = async (window: 7 | 30) => {
  const { data } = await api.get<WeightStats>(`/weights/stats`, { params: { window } })
  return data
}

export const upsertWeight = async (w: Weight) => {
  await api.post(`/weights`, w)
}

export const deleteWeight = async (date: string) => {
  await api.delete(`/weights/${date}`)
}

export const getExercises = async (range: RangeKey) => {
  const { data } = await api.get<Exercise[]>(`/exercises`, { params: { range } })
  return data
}

export const getExercisesDaily = async (range: RangeKey) => {
  const { data } = await api.get<DailyExercise[]>(`/exercises/daily`, { params: { range } })
  return data
}

export const getExercisesByActivity = async (range: RangeKey) => {
  const { data } = await api.get<Exercise[]>(`/exercises/by-activity`, { params: { range } })
  return data
}

export const upsertExercise = async (ex: Exercise) => {
  await axios.post(`/exercises`, ex)
}

export const deleteExerciseByKey = async (date: string, activity: string) => {
  await api.delete(`/exercises/by-key`, { params: { date, activity } })
}

export const getGoalWeight = async () => {
  const { data } = await api.get<{ goal_weight: number | null }>(`/settings/goal-weight`)
  return data.goal_weight
}

export const setGoalWeight = async (goal_weight: number) => {
  await api.post(`/settings/goal-weight`, { goal_weight })
}

