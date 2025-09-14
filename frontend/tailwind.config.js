/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          light: "#4C7AF2",
          dark: "#4DD0E1",
        },
      },
    },
  },
  darkMode: 'class',
  plugins: [],
}

