import React, { useEffect, useMemo, useState } from 'react'
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import Button from '../components/ui/Button'

type Status = 'todo' | 'doing' | 'done'
type Task = { id: string; title: string; status: Status }

const columns: { key: Status; label: string }[] = [
  { key: 'todo', label: 'To Do' },
  { key: 'doing', label: 'Doing' },
  { key: 'done', label: 'Done' },
]

function SortableCard({ id, title }: { id: string; title: string }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
  }
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners} className="rounded-md border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/70 px-3 py-2 text-sm cursor-grab">
      {title}
    </div>
  )
}

export function KanbanBoard() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [input, setInput] = useState('')

  useEffect(() => {
    const raw = localStorage.getItem('kanban_tasks')
    if (raw) {
      try { setTasks(JSON.parse(raw)) } catch {}
    }
  }, [])
  useEffect(() => {
    localStorage.setItem('kanban_tasks', JSON.stringify(tasks))
  }, [tasks])

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))

  const idsByColumn = useMemo(() => {
    const map: Record<Status, string[]> = { todo: [], doing: [], done: [] }
    tasks.forEach(t => map[t.status].push(t.id))
    return map
  }, [tasks])

  function onDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over) return

    const [fromCol, fromIdx] = findLocation(active.id as string)
    const [toCol, toIdx] = findLocation(over.id as string) || [fromCol, fromIdx]

    if (fromCol === toCol) {
      // reorder in same column
      const colIds = [...idsByColumn[fromCol]]
      const oldIndex = colIds.indexOf(active.id as string)
      const newIndex = colIds.indexOf(over.id as string)
      const newColIds = arrayMove(colIds, oldIndex, newIndex)
      const newTasks = [...tasks]
      let cursor = 0
      newTasks
        .filter(t => t.status === fromCol)
        .forEach((t, i) => { t.id = newColIds[i] })
      setTasks(newTasks)
    } else {
      // move across columns: update status
      setTasks(prev => prev.map(t => (t.id === active.id ? { ...t, status: toCol } : t)))
    }
  }

  function findLocation(id: string): [Status, number] | null {
    for (const c of columns) {
      const idx = idsByColumn[c.key].indexOf(id)
      if (idx >= 0) return [c.key, idx]
    }
    return null
  }

  function addTask() {
    const title = input.trim()
    if (!title) return
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    setTasks(prev => [{ id, title, status: 'todo' }, ...prev])
    setInput('')
  }

  function clearDone() {
    setTasks(prev => prev.filter(t => t.status !== 'done'))
  }

  return (
    <div className="card p-4 h-[420px] flex flex-col">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-medium">🗂️ タスクボード</h2>
          <div className="flex items-center gap-2">
          <input value={input} onChange={e => setInput(e.target.value)} placeholder="タスクを追加" className="px-2 py-1 text-sm rounded border border-slate-300 dark:border-slate-600 bg-white/80 dark:bg-slate-800/70" />
          <Button className="text-xs" onClick={addTask}>追加</Button>
          <Button variant="muted" className="text-xs" onClick={clearDone}>完了をクリア</Button>
          </div>
        </div>
      <DndContext sensors={sensors} onDragEnd={onDragEnd}>
        <div className="grid grid-cols-3 gap-3 flex-1 overflow-auto">
          {columns.map(col => (
            <div key={col.key} className="rounded-lg border border-slate-200 dark:border-slate-700 p-2 bg-white/60 dark:bg-slate-800/50">
              <div className="text-xs opacity-70 mb-2">{col.label}</div>
              <SortableContext items={idsByColumn[col.key]} strategy={verticalListSortingStrategy}>
                <div className="flex flex-col gap-2">
                  {tasks.filter(t => t.status === col.key).map(t => (
                    <SortableCard key={t.id} id={t.id} title={t.title} />
                  ))}
                </div>
              </SortableContext>
            </div>
          ))}
        </div>
      </DndContext>
    </div>
  )
}
