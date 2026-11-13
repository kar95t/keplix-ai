/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        orbit: {
          900: "#090d16",
          800: "#0f172a",
          700: "#1e293b",
          cyan: "#38bdf8",
          teal: "#2dd4bf",
        }
      }
    },
  },
  plugins: [],
};

