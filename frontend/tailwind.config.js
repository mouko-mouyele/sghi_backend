/** @type {import('tailwindcss').Config} */

export default {

  darkMode: 'class',

  content: ['./index.html', './src/**/*.{vue,js}'],

  theme: {

    extend: {

      colors: {

        primary: {

          50: '#eef9ff',

          100: '#d9f1ff',

          200: '#bce7ff',

          300: '#8ed8ff',

          400: '#59c0ff',

          500: '#33a1ff',

          600: '#1a7ff5',

          700: '#1369e1',

          800: '#1655b6',

          900: '#18498f',

          950: '#132d57',

        },

        accent: {

          400: '#34d399',

          500: '#10b981',

          600: '#059669',

        },

      },

      fontFamily: {

        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],

        display: ['"Outfit"', 'system-ui', 'sans-serif'],

      },

      boxShadow: {

        card: '0 4px 24px -4px rgba(19, 105, 225, 0.12)',

        'card-dark': '0 4px 24px -4px rgba(0, 0, 0, 0.45)',

        glow: '0 0 40px -10px rgba(51, 161, 255, 0.4)',

        'glow-dark': '0 0 40px -10px rgba(51, 161, 255, 0.25)',

      },

    },

  },

  plugins: [],

}

