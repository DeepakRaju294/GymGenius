/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'], 
  theme: {
    extend: {
      fontFamily: {
        sans: ['Poppins', 'sans-serif'],
        hand: ['"Patrick Hand"', 'cursive'],
      },
      colors: {
        gymGreen: '#00C86F',
      },
      borderRadius: {
        lg: '1rem', 
      },
    },
  },
  plugins: [], 
};
