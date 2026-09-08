/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./app/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "hsl(var(--primary-hue) / <alpha-value>)",
        secondary: "hsl(var(--secondary-hue) / <alpha-value>)",
        accent: "hsl(var(--accent-hue) / <alpha-value>)",
        "primary-hover": "hsl(var(--primary-hue) / 0.85)",
        "primary-light": "hsl(var(--primary-hue) / 0.15)",
        "primary-dark": "hsl(var(--primary-hue) / 0.75)",
        "secondary-hover": "hsl(var(--secondary-hue) / 0.85)",
        "secondary-light": "hsl(var(--secondary-hue) / 0.15)",
      },
    },
  },
  plugins: [],
};
