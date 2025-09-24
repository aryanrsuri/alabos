import { clsx } from 'clsx'
import { forwardRef } from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
  asChild?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', children, asChild = false, ...props }, ref) => {
    const Component = asChild ? 'span' : 'button'

    return (
      <Component
        className={clsx(
          'inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none',
          {
            'bg-primary-600 hover:bg-primary-700 text-white focus:ring-primary-500': variant === 'primary',
            'bg-gray-200 hover:bg-gray-300 text-gray-900 focus:ring-gray-500': variant === 'secondary',
            'border border-gray-300 bg-white hover:bg-gray-50 text-gray-900 focus:ring-primary-500': variant === 'outline',
            'px-3 py-1.5 text-sm': size === 'sm',
            'px-4 py-2 text-sm': size === 'md',
            'px-6 py-3 text-base': size === 'lg',
          },
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </Component>
    )
  }
)

Button.displayName = 'Button'
