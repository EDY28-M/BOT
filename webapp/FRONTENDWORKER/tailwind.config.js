/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#2563EB',
        'primary-light': '#3B82F6',
        'primary-dark': '#1D4ED8',
        accent: '#0EA5E9',
        success: '#16A34A',
        danger: '#DC2626',
        warning: '#F59E0B',
      },
      fontFamily: {
        display: ['Inter', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.1)',
        'btn': '0 1px 2px rgba(37,99,235,0.2)',
      },
      keyframes: {
        'progress-stripes': {
          '0%': { backgroundPosition: '1rem 0' },
          '100%': { backgroundPosition: '0 0' },
        },
        blink: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.3 },
        },
      },
      animation: {
        'progress-stripes': 'progress-stripes 1s linear infinite',
        blink: 'blink 1s infinite',
      },
    },
  },
  plugins: [],
}
