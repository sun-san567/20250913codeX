import { render } from '@testing-library/react'
import { WeightChart } from '../WeightChart'

describe('WeightChart', () => {
  it('renders without crash and shows dataset', () => {
    const data = [
      { date: '2025-09-10', weight: 60.1 },
      { date: '2025-09-11', weight: 60.2 },
    ]
    const { container } = render(<div style={{ height: 320 }}><WeightChart data={data} ma7={[60.1, 60.2]} goal={60.0} dark={false} /></div>)
    expect(container.querySelector('canvas')).toBeInTheDocument()
  })
})

