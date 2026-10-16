/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0284c7',
          600: '#0369a1',
          700: '#075985',
          800: '#0c4a6e',
          900: '#082f49',
          950: '#041d30',
        },
        surface: {
          canvas: '#090d16',
          card: '#0d1322',
          elevated: '#131b2e',
          subtle: '#182238',
          border: '#1c263c',
          'border-strong': '#273553',
          'border-subtle': '#151e30',
        },
        automotive: {
          dark: '#090d16',
          card: '#0d1322',
          elevated: '#131b2e',
          border: '#1c263c',
          accent: '#0284c7',
          teal: '#0d9488',
          amber: '#d97706',
          emerald: '#059669',
        }
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif'
        ],
        mono: [
          'JetBrains Mono',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace'
        ]
      }
    },
  },
  plugins: [],
}

