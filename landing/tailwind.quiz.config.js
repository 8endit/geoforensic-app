/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./quiz.html'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef4ff',
          100: '#d9e5ff',
          200: '#bcd2ff',
          500: '#3b6fce',
          600: '#1e3a6e',
          700: '#162d56',
          800: '#0f2040',
          900: '#0a1628',
        },
        accent: {
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
