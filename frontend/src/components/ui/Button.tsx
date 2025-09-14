import React, { ButtonHTMLAttributes, useCallback } from 'react'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'modern' | 'muted' | 'primary'
}

export default function Button({ variant = 'modern', className = '', onClick, children, ...rest }: Props) {
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      // Ripple effect
      const btn = e.currentTarget
      const rect = btn.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top
      const span = document.createElement('span')
      span.className = 'ripple'
      ;(span.style as any).left = `${x}px`
      ;(span.style as any).top = `${y}px`
      btn.appendChild(span)
      setTimeout(() => span.remove(), 650)

      onClick?.(e)
    },
    [onClick]
  )

  const base = variant === 'modern' ? 'btn-modern' : variant === 'primary' ? 'btn btn-primary' : 'btn btn-muted'

  return (
    <button className={`${base} ${className}`} onClick={handleClick} {...rest}>
      {children}
    </button>
  )
}

