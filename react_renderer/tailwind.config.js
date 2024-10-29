/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      // Keep your existing theme extensions
      animation: {
        'tick': 'tick 1s linear infinite',
      },
      keyframes: {
        tick: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
  safelist: [
    'w-1',
    'w-2',
    'w-3',
    'w-4',
    'h-32',
    'h-40',
    'h-48',
    'rounded-full',
    'bg-gray-800',
    'bg-red-500',
    'bg-blue-500',
    'bg-pink-500',
    'bg-gray-400',
    'border-gray-800',
    'border-blue-500',
    'border-gray-400',
    'bg-slate-100',
    'bg-blue-50',
    'bg-gray-50',
    'transform-gpu',
    'transition-transform',
    'duration-100',
    'duration-700',
    'duration-1000',
    'ease-linear',
    'ease-in-out',
  ],
}