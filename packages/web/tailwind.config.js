/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        display: ['Instrument Sans', 'DM Sans', 'system-ui', 'sans-serif'],
        mono: ['DM Mono', 'ui-monospace', 'monospace'],
      },
      screens: {
        md: '768px',
        lg: '1024px',
      },
      borderRadius: { sm: '0.25rem' },
      boxShadow: {
        card: '0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.06)',
        cardHover: '0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.06)',
        dsSm: 'var(--shadow-sm)',
        dsMd: 'var(--shadow-md)',
        dsLg: 'var(--shadow-lg)',
      },
    },
  },
  plugins: [],
}
