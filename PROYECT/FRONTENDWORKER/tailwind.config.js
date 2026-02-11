/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#a855f7',
        'primary-dim': '#a855f720',
        'bg-dark': '#0b1120',
        'neon-green': '#00ff9d',
        'neon-blue': '#00f3ff',
        'neon-red': '#ff0055',
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
      boxShadow: {
        'neon-primary': '0 0 10px #a855f7, 0 0 20px #a855f740',
        'neon-green': '0 0 8px #00ff9d, 0 0 15px #00ff9d40',
        'neon-blue': '0 0 8px #00f3ff, 0 0 15px #00f3ff40',
        'neon-red': '0 0 8px #ff0055, 0 0 15px #ff005540',
      },
      keyframes: {
        'pulse-green': {
          '0%': { boxShadow: '0 0 0 0 rgba(0,255,157,0.7)' },
          '70%': { boxShadow: '0 0 0 6px rgba(0,255,157,0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(0,255,157,0)' },
        },
        'pulse-blue': {
          '0%': { boxShadow: '0 0 0 0 rgba(0,243,255,0.7)' },
          '70%': { boxShadow: '0 0 0 6px rgba(0,243,255,0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(0,243,255,0)' },
        },
        'progress-stripes': {
          '0%': { backgroundPosition: '1rem 0' },
          '100%': { backgroundPosition: '0 0' },
        },
        blink: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.15 },
        },
      },
      animation: {
        'pulse-green': 'pulse-green 2s infinite',
        'pulse-blue': 'pulse-blue 2s infinite 0.5s',
        'progress-stripes': 'progress-stripes 1s linear infinite',
        blink: 'blink 1s infinite',
      },
    },
  },
  plugins: [],
}
