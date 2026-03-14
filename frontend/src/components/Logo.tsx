'use client'

interface LogoProps {
  size?: 'sm' | 'md' | 'lg'
  showText?: boolean
  className?: string
}

const sizeMap = {
  sm: { icon: 24, text: 'text-sm' },
  md: { icon: 28, text: 'text-base' },
  lg: { icon: 36, text: 'text-xl' },
}

export default function Logo({ size = 'md', showText = true, className = '' }: LogoProps) {
  const { icon: iconSize, text: textClass } = sizeMap[size]

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="flex-shrink-0"
      >
        <defs>
          <linearGradient id={`bg-${size}`} x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#1E293B"/>
            <stop offset="100%" stopColor="#0F172A"/>
          </linearGradient>
          <linearGradient id={`bar-${size}`} x1="0" y1="26" x2="0" y2="6" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#3B82F6"/>
            <stop offset="100%" stopColor="#60A5FA"/>
          </linearGradient>
        </defs>
        <rect width="32" height="32" rx="6" fill={`url(#bg-${size})`}/>
        <rect x="5" y="19" width="4" height="6" rx="1" fill={`url(#bar-${size})`} opacity="0.45"/>
        <rect x="10.5" y="16" width="4" height="9" rx="1" fill={`url(#bar-${size})`} opacity="0.6"/>
        <rect x="16" y="12.5" width="4" height="12.5" rx="1" fill={`url(#bar-${size})`} opacity="0.75"/>
        <rect x="21.5" y="9" width="4" height="16" rx="1" fill={`url(#bar-${size})`} opacity="0.9"/>
        <path d="M7 17.5 L12.5 14 L18 10.5 L23.5 7" stroke="#A78BFA" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        <circle cx="23.5" cy="7" r="1.8" fill="#A78BFA"/>
        <circle cx="26" cy="23" r="3.5" fill="#10B981"/>
        <path d="M24.5 23 L25.5 24 L27.5 22" stroke="white" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
      </svg>
      {showText && (
        <span className={`${textClass} font-extrabold tracking-tight text-white`}>
          BACKTESTED
        </span>
      )}
    </div>
  )
}
