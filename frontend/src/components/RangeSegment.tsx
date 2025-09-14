import React from 'react'
import type { RangeKey } from '../api/types'

const options: { label: string; key: RangeKey }[] = [
  { label: '1週間', key: '7d' },
  { label: '1ヶ月', key: '30d' },
  { label: '3ヶ月', key: '90d' },
  { label: '半年', key: '180d' },
  { label: '1年', key: '365d' },
  { label: '全期間', key: 'all' },
]

export function RangeSegment({ value, onChange }: { value: RangeKey; onChange: (k: RangeKey) => void }) {
  return (
    <div className="segmented">
      {options.map((o) => (
        <button
          key={o.key}
          className={o.key === value ? 'active' : ''}
          onClick={() => onChange(o.key)}
          type="button"
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

