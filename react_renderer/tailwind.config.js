/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
  // Important to avoid conflicts with MUI
  important: true,
  // Don't purge these utility classes as they might be used dynamically
  safelist: [
    'bg-blue-500',
    'text-white',
    'hover:bg-blue-600',
    {
      pattern: /(bg|text|border)-(primary|secondary|success|error|warning|info)-.*/,
    },
  ],
}