/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['Outfit', 'sans-serif'],
      },
      colors: {
        app: '#08090d',
        cardbg: 'rgba(18, 20, 28, 0.65)',
        borderglow: 'rgba(0, 240, 255, 0.35)',
        neoncyan: '#00f0ff',
        neonpurple: '#bd00ff',
        neonemerald: '#00ff88',
        neonred: '#ff3b30',
      },
      boxShadow: {
        neon: '0 0 15px rgba(0, 240, 255, 0.25)',
        neongreen: '0 0 15px rgba(0, 255, 136, 0.25)',
        mainshadow: '0 8px 32px 0 rgba(0, 0, 0, 0.4)',
      }
    },
  },
  plugins: [],
}
