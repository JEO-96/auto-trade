/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  safelist: [
    'bg-primary/10', 'bg-secondary/10', 'bg-accent/10',
    'border-primary/10', 'border-secondary/10', 'border-accent/10',
    'text-primary', 'text-secondary', 'text-accent',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--bg)',
        surface: {
          DEFAULT: 'var(--surface)',
          lighter: 'var(--surface-lighter)',
        },
        primary: {
          DEFAULT: '#3B82F6',
          dark: '#2563EB',
          light: '#60A5FA',
        },
        secondary: {
          DEFAULT: '#10B981',
          dark: '#059669',
          light: '#34D399',
        },
        accent: {
          DEFAULT: '#8B5CF6',
          dark: '#7C3AED',
          light: '#A78BFA',
        },
        danger: '#EF4444',
        /* Theme-aware semantic colors */
        'th-text': 'var(--text)',
        'th-text-secondary': 'var(--text-secondary)',
        'th-text-muted': 'var(--text-muted)',
        'th-border': 'var(--border)',
        'th-border-light': 'var(--border-light)',
        'th-hover': 'var(--hover)',
        'th-card': 'var(--card)',
        'th-overlay': 'var(--overlay)',
        'th-modal': 'var(--modal)',
        'th-input': 'var(--input)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out forwards',
        'fade-in-up': 'fadeInUp 0.4s cubic-bezier(0.25, 1, 0.5, 1) forwards',
        'slide-in-left': 'slideInLeft 0.35s cubic-bezier(0.25, 1, 0.5, 1) forwards',
        'scale-in': 'scaleIn 0.3s cubic-bezier(0.25, 1, 0.5, 1) forwards',
        'glow-pulse': 'glowPulse 3s infinite ease-in-out',
        'float': 'float 6s infinite ease-in-out',
        'live-dot': 'liveDot 2s infinite ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInLeft: {
          '0%': { opacity: '0', transform: 'translateX(-16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        glowPulse: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.7' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        liveDot: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.4', transform: 'scale(0.85)' },
        },
      },
      boxShadow: {
        'glass': '0 4px 24px 0 rgba(0, 0, 0, 0.2)',
        'glow-primary': '0 0 16px rgba(59, 130, 246, 0.4)',
        'glow-secondary': '0 0 16px rgba(16, 185, 129, 0.4)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
